"""
Claude Agent SDK integration for shader generation.

Uses Claude to generate Shadertoy-style GLSL shaders based on
text descriptions, with tools to compile and render the shaders.
"""

import asyncio
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .tools import create_shader_tools, set_render_context, get_render_context


# Maximum number of agent turns before giving up
MAX_TURNS = 10

# System prompt for the shader generation agent
SYSTEM_PROMPT = """You are an expert GLSL shader programmer specializing in Shadertoy-style visual effects.

Your task is to create a fragment shader that produces the requested visual effect.

## Shader Format Requirements

Your shader MUST follow this exact format:

```glsl
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // Your shader code here
    // fragCoord: pixel coordinates (0 to iResolution.xy)
    // fragColor: output color (RGBA, with alpha for transparency)
}
```

## Available Uniforms

- `iTime` (float): Current time in seconds (0 to duration)
- `iResolution` (vec3): Viewport resolution (width, height, 1.0)

## Important Guidelines

1. **Transparency**: Use the alpha channel (fragColor.a) for transparency. Pixels where the effect doesn't appear should have alpha = 0.0.

2. **Animation Timing**: The animation runs from iTime=0 to iTime=duration. Design your effect to complete within this timeframe.

3. **Coordinate System**: fragCoord goes from (0,0) at bottom-left to (iResolution.xy) at top-right. Normalize with: `vec2 uv = fragCoord / iResolution.xy;`

4. **Performance**: Keep shaders efficient - avoid excessive loops or complex operations.

## Workflow

1. First, write your shader code and use `compile_shader` to check for errors
2. Use `render_frame` to see the result at different time values (e.g., 0.0, 0.5, 1.0)
3. Iterate on the shader until the effect looks good
4. Finally, use `render_animation` to save the complete animation

Always test your shader before declaring it complete!"""


def build_prompt(
    effect_description: str,
    duration: float,
    width: int,
    height: int
) -> str:
    """Build the user prompt for shader generation."""
    return f"""Create a visual effect animation: "{effect_description}"

Specifications:
- Duration: {duration} seconds (iTime goes from 0 to {duration})
- Resolution: {width} x {height} pixels
- Output: Transparent background (alpha = 0 where no effect)

Please:
1. Write the shader code
2. Compile it to check for errors
3. Render a few test frames to verify it looks correct
4. Render the final animation when satisfied

Begin by writing the shader code for this effect."""


async def generate_vfx(
    prompt: str,
    duration: float = 1.0,
    resolution: Tuple[int, int] = (256, 256),
    frames: int = 10,
    output_path: str = "output.gif",
    max_retries: int = 3,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Generate a visual effect animation using Claude.

    Args:
        prompt: Description of the visual effect (e.g., "fiery explosion")
        duration: Animation duration in seconds
        resolution: (width, height) tuple
        frames: Number of frames to generate
        output_path: Path to save the output GIF
        max_retries: Maximum retry attempts if generation fails
        verbose: Print progress messages

    Returns:
        Dictionary with:
            - gif_path: Path to the generated GIF
            - shader_path: Path to the saved shader code
            - shader_code: The generated GLSL shader code
            - success: Whether generation was successful
            - error: Error message if failed
    """
    try:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
    except ImportError:
        raise ImportError(
            "claude-agent-sdk is required. Install it with: pip install claude-agent-sdk"
        )

    width, height = resolution

    # Set up the rendering context for tools
    set_render_context(width, height, duration, frames, output_path)

    # Create the shader tools and MCP server
    shader_server, allowed_tools = create_shader_tools()

    # Build the prompt
    user_prompt = build_prompt(prompt, duration, width, height)

    # Configure the agent
    options = ClaudeAgentOptions(
        mcp_servers={"shader-tools": shader_server},
        allowed_tools=allowed_tools,
        max_turns=MAX_TURNS,
        system_prompt=SYSTEM_PROMPT,
    )

    attempt = 0
    last_error = None

    while attempt < max_retries:
        attempt += 1

        if verbose:
            print(f"Attempt {attempt}/{max_retries}...")

        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(user_prompt)

                # Process the response
                async for message in client.receive_response():
                    if verbose and hasattr(message, 'content'):
                        # Print text content for debugging
                        for block in getattr(message, 'content', []):
                            if hasattr(block, 'text'):
                                print(f"Claude: {block.text[:200]}...")

                # Check if the animation was rendered
                ctx = get_render_context()
                output_file = Path(output_path)
                shader_file = output_file.with_suffix('.glsl')

                if output_file.exists() and shader_file.exists():
                    if verbose:
                        print(f"Success! Generated {output_path}")

                    return {
                        "gif_path": str(output_file),
                        "shader_path": str(shader_file),
                        "shader_code": ctx.get("shader_code", ""),
                        "success": True,
                        "error": None
                    }
                else:
                    last_error = "Agent did not produce output files"
                    if verbose:
                        print(f"Warning: {last_error}")

        except Exception as e:
            last_error = str(e)
            if verbose:
                print(f"Error: {last_error}")

    # All retries exhausted
    return {
        "gif_path": None,
        "shader_path": None,
        "shader_code": None,
        "success": False,
        "error": f"Failed after {max_retries} attempts. Last error: {last_error}"
    }


async def generate_vfx_with_feedback(
    prompt: str,
    duration: float = 1.0,
    resolution: Tuple[int, int] = (256, 256),
    frames: int = 10,
    output_path: str = "output.gif",
    on_progress: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Generate VFX with progress callbacks.

    Similar to generate_vfx but allows for progress monitoring.

    Args:
        prompt: Description of the visual effect
        duration: Animation duration in seconds
        resolution: (width, height) tuple
        frames: Number of frames to generate
        output_path: Path to save the output GIF
        on_progress: Optional callback function(message: str) for progress updates

    Returns:
        Same as generate_vfx
    """
    def progress(msg: str):
        if on_progress:
            on_progress(msg)

    progress(f"Starting VFX generation: {prompt}")
    progress(f"Settings: {resolution[0]}x{resolution[1]}, {frames} frames, {duration}s duration")

    result = await generate_vfx(
        prompt=prompt,
        duration=duration,
        resolution=resolution,
        frames=frames,
        output_path=output_path,
        verbose=True
    )

    if result["success"]:
        progress(f"Generated successfully: {result['gif_path']}")
    else:
        progress(f"Generation failed: {result['error']}")

    return result
