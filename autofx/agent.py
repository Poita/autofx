"""
Claude Agent SDK integration for shader generation.

Uses Claude to generate Shadertoy-style GLSL shaders based on
text descriptions, with tools to compile and render the shaders.
"""

import asyncio
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .tools import create_shader_tools, set_render_context, get_render_context


# Model to use for shader generation
MODEL = "claude-opus-4-5-20251101"

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

4. **HIGH QUALITY - Performance is NOT a concern**: This is pre-rendered offline, NOT real-time. Go all out on quality! Use complex noise functions (FBM, Perlin, Simplex), multiple layers, many particles, ray marching, whatever produces the best visual result. Don't hold back - more iterations, more detail, more sophistication. Production quality is the goal.

5. **CRITICAL - Frame Bounds**: The ENTIRE effect must fit fully within the frame at ALL times during the animation. Use normalized UV coordinates (0.0 to 1.0) and ensure no part of the effect extends beyond the edges. Add padding/margins if needed (e.g., keep effects within 0.1 to 0.9 range). Check your test frames carefully to verify nothing is cut off!

## Workflow

1. First, write your shader code and use `compile_shader` to check for errors
2. Use `render_frame` to see the result at different time values (e.g., 0.0, 0.5, 1.0)
3. Iterate on the shader until the effect looks good AND fits fully within frame
4. Finally, use `render_animation` to save the complete animation

Always test your shader before declaring it complete!"""


def build_prompt(
    effect_description: str,
    duration: float,
    width: int,
    height: int,
    loop: bool = False
) -> str:
    """Build the user prompt for shader generation."""
    if loop:
        timing_instruction = f"""- Duration: {duration} seconds (iTime goes from 0 to {duration})
- LOOPING: This effect MUST seamlessly loop! Requirements:
  - The FINAL frame (t={duration}) must be IDENTICAL to the FIRST frame (t=0)
  - ALL animated values must use cyclic functions (sin, cos, fract)
  - Use this pattern: sin(iTime * 2.0 * 3.14159 / {duration}) to complete exactly one cycle
  - Or use: fract(iTime / {duration}) for linear cycling values
  - EVERY time-based variable must cycle back to its starting value
  - Test by comparing t=0 and t={duration} frames - they should look identical!"""
    else:
        timing_instruction = f"""- Duration: {duration} seconds (iTime goes from 0 to {duration})
- NON-LOOPING: This is a one-shot effect that must COMPLETE within the duration. The effect should:
  - Start at t=0 (can fade in)
  - Reach its peak/climax around the middle
  - Fully dissipate/fade out to completely transparent (alpha=0 everywhere) by t={duration}
  - At the final frame, NOTHING should be visible - the effect is DONE"""

    return f"""Create a visual effect animation: "{effect_description}"

Specifications:
{timing_instruction}
- Resolution: {width} x {height} pixels
- Output: Transparent background (alpha = 0 where no effect)
- IMPORTANT: The effect must fit ENTIRELY within the frame bounds at all times. Nothing should be cut off at the edges!

Please:
1. Write the shader code (center the effect, add margins to keep it within bounds)
2. Compile it to check for errors
3. Render test frames at t=0, t=middle, t=end to verify it looks correct AND fits within frame
4. CRITICAL VERIFICATION:
   - For NON-LOOPING effects: verify the FINAL frame is completely transparent (nothing visible)
   - For LOOPING effects: verify t=0 and t=end frames are IDENTICAL (compare them carefully!)
5. Render the final animation when satisfied

Begin by writing the shader code for this effect."""


async def generate_vfx(
    prompt: str,
    duration: float = 1.0,
    resolution: Tuple[int, int] = (256, 256),
    frames: int = 10,
    output_path: str = "output.gif",
    verbose: bool = False,
    loop: bool = False
) -> Dict[str, Any]:
    """
    Generate a visual effect animation using Claude.

    Args:
        prompt: Description of the visual effect (e.g., "fiery explosion")
        duration: Animation duration in seconds
        resolution: (width, height) tuple
        frames: Number of frames to generate
        output_path: Path to save the output GIF
        verbose: Print progress messages
        loop: If True, create a seamlessly looping effect; if False, effect dissipates by end

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
    user_prompt = build_prompt(prompt, duration, width, height, loop=loop)

    # Configure the agent (no max_turns - let it work until done)
    options = ClaudeAgentOptions(
        model=MODEL,
        mcp_servers={"shader-tools": shader_server},
        allowed_tools=allowed_tools,
        system_prompt=SYSTEM_PROMPT,
    )

    try:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)

            # Process the response
            async for message in client.receive_response():
                if verbose and hasattr(message, 'content'):
                    # Print text content for debugging
                    for block in getattr(message, 'content', []):
                        if hasattr(block, 'text'):
                            print(block.text)

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
                return {
                    "gif_path": None,
                    "shader_path": None,
                    "shader_code": None,
                    "success": False,
                    "error": "Agent did not produce output files"
                }

    except Exception as e:
        return {
            "gif_path": None,
            "shader_path": None,
            "shader_code": None,
            "success": False,
            "error": str(e)
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
