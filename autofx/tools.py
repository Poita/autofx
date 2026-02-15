"""
MCP tools for the shader generation agent.

These tools allow Claude to:
- Compile and validate GLSL shaders
- Render single frames and see the output
- Render full animations
"""

from typing import Any, Dict, Tuple, Optional
import base64
import io
from pathlib import Path

from .renderer import ShaderRenderer, compile_shader as _compile_shader
from .gif import frame_to_base64_png, save_gif
from .timing import get_timer


# Global state for the current rendering context
_current_context: Optional[Dict[str, Any]] = None


def set_render_context(
    width: int,
    height: int,
    duration: float,
    num_frames: int,
    output_path: str,
    seed: float = 0.0
) -> None:
    """
    Set the rendering context for tools to use.

    This must be called before using the tools.
    """
    global _current_context
    _current_context = {
        "width": width,
        "height": height,
        "duration": duration,
        "num_frames": num_frames,
        "output_path": output_path,
        "seed": seed,
        "shader_code": None,
    }


def get_render_context() -> Dict[str, Any]:
    """Get the current rendering context."""
    if _current_context is None:
        raise RuntimeError("Render context not set. Call set_render_context first.")
    return _current_context


def create_shader_tools():
    """
    Create the shader tools for the agent.

    Returns a list of tool definitions that can be passed to create_sdk_mcp_server.
    """
    try:
        from claude_agent_sdk import tool, create_sdk_mcp_server
    except ImportError:
        raise ImportError(
            "claude-agent-sdk is required. Install it with: pip install claude-agent-sdk"
        )

    @tool(
        "compile_shader",
        "Compile and validate a Shadertoy-style GLSL shader. Returns success or error messages.",
        {"shader_code": str}
    )
    async def compile_shader_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Compile a shader and check for errors."""
        shader_code = args["shader_code"]
        ctx = get_render_context()
        timer = get_timer()

        with timer.phase("compile_shader (tool call)"):
            success, error = _compile_shader(shader_code, ctx["width"], ctx["height"])

        if success:
            # Store the shader code for later use
            ctx["shader_code"] = shader_code
            return {
                "content": [{
                    "type": "text",
                    "text": "Shader compiled successfully! You can now render frames with render_frame or render_animation."
                }]
            }
        else:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Shader compilation failed:\n{error}\n\nPlease fix the errors and try again."
                }]
            }

    @tool(
        "render_frame",
        "Render a single frame of the shader at a specific time. Returns the image so you can see the result.",
        {"shader_code": str, "time": float}
    )
    async def render_frame_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Render a single frame and return it as an image."""
        import time as time_mod
        shader_code = args["shader_code"]
        time = args["time"]
        ctx = get_render_context()
        timer = get_timer()

        try:
            t0 = time_mod.monotonic()
            with ShaderRenderer(ctx["width"], ctx["height"]) as renderer:
                frame = renderer.render(shader_code, time, ctx.get("seed", 0.0))
                png_base64 = frame_to_base64_png(frame)
            timer.record(f"render_frame t={time:.2f}s (tool call)", time_mod.monotonic() - t0)

            # Store the shader code
            ctx["shader_code"] = shader_code

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Frame rendered at time={time}s. Resolution: {ctx['width']}x{ctx['height']}."
                    },
                    {
                        "type": "image",
                        "data": png_base64,
                        "mimeType": "image/png"
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Failed to render frame: {str(e)}"
                }]
            }

    @tool(
        "render_animation",
        "Render the full animation and save it as a GIF. This is the final step after you're satisfied with the shader.",
        {"shader_code": str}
    )
    async def render_animation_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Render all frames and save as GIF."""
        import time as time_mod
        shader_code = args["shader_code"]
        ctx = get_render_context()
        timer = get_timer()

        try:
            t0 = time_mod.monotonic()
            with ShaderRenderer(ctx["width"], ctx["height"]) as renderer:
                frames = renderer.render_animation(
                    shader_code,
                    ctx["duration"],
                    ctx["num_frames"],
                    ctx.get("seed", 0.0)
                )
            timer.record(f"render_animation ({ctx['num_frames']} frames)", time_mod.monotonic() - t0)

            # Save the GIF
            t1 = time_mod.monotonic()
            save_gif(frames, ctx["output_path"], ctx["duration"])
            timer.record("save_gif", time_mod.monotonic() - t1)

            # Save the shader code
            shader_path = str(Path(ctx["output_path"]).with_suffix('.glsl'))
            with open(shader_path, 'w') as f:
                f.write(shader_code)

            # Store in context
            ctx["shader_code"] = shader_code

            # Create a preview showing first, middle, and last frames
            preview_frames = [
                frames[0],
                frames[len(frames) // 2],
                frames[-1]
            ]
            preview_images = []
            for i, frame in enumerate(preview_frames):
                preview_images.append({
                    "type": "image",
                    "data": frame_to_base64_png(frame),
                    "mimeType": "image/png"
                })

            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Animation rendered successfully!\n"
                            f"- GIF saved to: {ctx['output_path']}\n"
                            f"- Shader saved to: {shader_path}\n"
                            f"- Frames: {ctx['num_frames']}\n"
                            f"- Duration: {ctx['duration']}s\n"
                            f"- Resolution: {ctx['width']}x{ctx['height']}\n\n"
                            f"Preview frames (first, middle, last):"
                        )
                    },
                    *preview_images
                ]
            }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Failed to render animation: {str(e)}"
                }]
            }

    # Create the MCP server
    shader_server = create_sdk_mcp_server(
        name="shader-tools",
        version="1.0.0",
        tools=[compile_shader_tool, render_frame_tool, render_animation_tool]
    )

    return shader_server, [
        "mcp__shader-tools__compile_shader",
        "mcp__shader-tools__render_frame",
        "mcp__shader-tools__render_animation"
    ]
