"""
Claude Agent SDK integration for shader generation.

Uses Claude to generate Shadertoy-style GLSL shaders based on
text descriptions, with tools to compile and render the shaders.
"""

import asyncio
import time as time_mod
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .tools import create_shader_tools, set_render_context, get_render_context
from .timing import get_timer


# Default model for shader generation
DEFAULT_MODEL = "claude-opus-4-7"

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
- `iSeed` (float): Random seed for procedural variation (used when generating multiple variations)

## Important Guidelines

1. **Transparency**: Use the alpha channel (fragColor.a) for transparency. Pixels where the effect doesn't appear should have alpha = 0.0.

2. **Animation Timing**: The animation runs from iTime=0 to iTime=duration. Design your effect to complete within this timeframe.

3. **Coordinate System**: fragCoord goes from (0,0) at bottom-left to (iResolution.xy) at top-right. Normalize with: `vec2 uv = fragCoord / iResolution.xy;`

4. **HIGH QUALITY - Performance is NOT a concern**: This is pre-rendered offline, NOT real-time. Go all out on quality! Use complex noise functions (FBM, Perlin, Simplex), multiple layers, many particles, ray marching, whatever produces the best visual result. Don't hold back - more iterations, more detail, more sophistication. Production quality is the goal.

5. **NATURAL FRAMING - Design effects to fit naturally**: The effect should be self-contained and naturally fit within the frame WITHOUT artificial edge fading, vignettes, or smoothstep borders. Instead:
   - **Center and scale appropriately**: Design the effect to naturally occupy the frame with comfortable margins
   - **Bounded motion**: For particles, sparks, debris - design trajectories that stay within frame naturally (e.g., explode then fall back, orbit around center, rise and fade before reaching top)
   - **Self-limiting shapes**: Use shapes that have natural boundaries (circles, spheres, bounded noise patterns) rather than infinite patterns that need artificial cropping
   - **NO edge smoothstep/vignette**: Do NOT add `smoothstep(0.0, 0.1, uv.x)` style edge fading - this looks artificial. The effect itself should simply not extend to the edges.
   - **Transparent background**: Pixels where the effect doesn't appear should have alpha = 0.0

## Workflow

1. First, write your shader code and use `compile_shader` to check for errors
2. Use `render_frame` to see the result at different time values (e.g., 0.0, 0.5, 1.0)
3. **Check framing**: Verify the effect fits naturally within the frame. If elements are cut off at edges, redesign the effect's scale or motion - do NOT add artificial edge fading.
4. Iterate until the effect looks good with natural boundaries
5. Finally, use `render_animation` to save the complete animation

Always test your shader before declaring it complete!"""

# System prompt for editing existing shaders
EDIT_SYSTEM_PROMPT = """You are an expert GLSL shader programmer specializing in Shadertoy-style visual effects.

Your task is to MODIFY an existing shader according to the user's instructions while preserving the parts that work well.

## Shader Format Requirements

The shader MUST follow this exact format:

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
- `iSeed` (float): Random seed for procedural variation

## Important Guidelines

1. **Preserve What Works**: The existing shader already produces a working effect. Make targeted changes to achieve the requested modification without breaking what already works.

2. **Transparency**: Use the alpha channel (fragColor.a) for transparency. Pixels where the effect doesn't appear should have alpha = 0.0.

3. **Animation Timing**: The animation runs from iTime=0 to iTime=duration. Maintain proper timing behavior.

4. **HIGH QUALITY**: This is pre-rendered offline. Maintain or improve quality.

5. **NATURAL FRAMING**: The effect should fit naturally within the frame WITHOUT artificial edge fading or vignettes. Do NOT add smoothstep edge borders - the effect itself should simply not extend to the edges. If the existing shader has artificial edge fading, consider removing it if the effect can be redesigned to fit naturally.

## Workflow

1. Study the existing shader to understand its structure
2. Make the requested modifications
3. Use `compile_shader` to check for errors
4. Use `render_frame` to see the result at different time values (e.g., 0.0, 0.5, 1.0)
5. **Verify**: Check that the modification was successful and the effect fits naturally within the frame
6. Iterate if needed
7. Finally, use `render_animation` to save the complete animation

Always test your modified shader before declaring it complete!"""


def build_prompt(
    effect_description: str,
    duration: float,
    width: int,
    height: int,
    loop: bool = False,
    variations: int = 1
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

    # Add variations instruction if generating multiple variations
    if variations > 1:
        variations_instruction = f"""
- VARIATIONS: You are generating a shader that will be rendered {variations} times with different seeds.
  You MUST incorporate `iSeed` into any randomness in your shader (noise functions, hash functions,
  random particle positions, etc.). The same shader code will produce {variations} unique-looking
  animations by varying iSeed from 0 to {variations - 1}.

  Example patterns:
  - `hash(fragCoord + iSeed)` instead of `hash(fragCoord)`
  - `noise(uv * 10.0 + iSeed)` instead of `noise(uv * 10.0)`
  - `sin(iTime + iSeed * 6.28)` for phase-shifted animations

  Your effect MUST look different for each seed value while maintaining the same overall style."""
    else:
        variations_instruction = ""

    return f"""Create a visual effect animation: "{effect_description}"

Specifications:
{timing_instruction}{variations_instruction}
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


def build_edit_prompt(
    existing_shader: str,
    modification: str,
    duration: float,
    width: int,
    height: int,
    loop: bool = False
) -> str:
    """Build the user prompt for shader editing."""
    if loop:
        timing_instruction = f"""- Duration: {duration} seconds (iTime goes from 0 to {duration})
- LOOPING: The effect must seamlessly loop (final frame identical to first frame)"""
    else:
        timing_instruction = f"""- Duration: {duration} seconds (iTime goes from 0 to {duration})
- NON-LOOPING: One-shot effect that dissipates to fully transparent by the end"""

    return f"""Modify this shader: "{modification}"

## Existing Shader Code

```glsl
{existing_shader}
```

## Requirements
{timing_instruction}
- Resolution: {width} x {height} pixels
- Output: Transparent background (alpha = 0 where no effect)
- IMPORTANT: Keep edges fully transparent at all times

Please:
1. Study the existing shader to understand its structure
2. Make the requested modifications
3. Compile to check for errors
4. Render test frames at t=0, t=middle, t=end to verify the modification AND transparent edges
5. Render the final animation when satisfied

Begin by analyzing the shader and making the requested changes."""


async def generate_vfx(
    prompt: str,
    duration: float = 1.0,
    resolution: Tuple[int, int] = (256, 256),
    frames: int = 10,
    output_path: str = "output.gif",
    verbose: bool = False,
    loop: bool = False,
    variations: int = 1,
    model: Optional[str] = None
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
        variations: Number of variations to generate (tells agent to use iSeed if > 1)
        model: Model to use (default: claude-opus-4-7)

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
    user_prompt = build_prompt(prompt, duration, width, height, loop=loop, variations=variations)

    # Configure the agent (no max_turns - let it work until done)
    options = ClaudeAgentOptions(
        model=model or DEFAULT_MODEL,
        mcp_servers={"shader-tools": shader_server},
        allowed_tools=allowed_tools,
        system_prompt=SYSTEM_PROMPT,
    )

    timer = get_timer()

    try:
        t_agent_start = time_mod.monotonic()
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)

            # Process the response
            async for message in client.receive_response():
                if verbose and hasattr(message, 'content'):
                    # Print text content for debugging
                    for block in getattr(message, 'content', []):
                        if hasattr(block, 'text'):
                            print(block.text)

        t_agent_total = time_mod.monotonic() - t_agent_start
        # Calculate agent thinking time = total agent time minus tool call times
        tool_time = sum(e["elapsed"] for e in timer.events)
        timer.record("claude agent (thinking + API)", t_agent_total - tool_time)

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


async def edit_vfx(
    existing_shader: str,
    modification: str,
    duration: float = 1.0,
    resolution: Tuple[int, int] = (256, 256),
    frames: int = 10,
    output_path: str = "output.gif",
    verbose: bool = False,
    loop: bool = False,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Edit an existing shader using Claude.

    Args:
        existing_shader: The existing GLSL shader code to modify
        modification: Description of the changes to make
        duration: Animation duration in seconds
        resolution: (width, height) tuple
        frames: Number of frames to generate
        output_path: Path to save the output GIF
        verbose: Print progress messages
        loop: If True, create a seamlessly looping effect; if False, effect dissipates by end
        model: Model to use (default: claude-opus-4-7)

    Returns:
        Dictionary with:
            - gif_path: Path to the generated GIF
            - shader_path: Path to the saved shader code
            - shader_code: The modified GLSL shader code
            - success: Whether editing was successful
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

    # Build the edit prompt
    user_prompt = build_edit_prompt(existing_shader, modification, duration, width, height, loop=loop)

    # Configure the agent with edit system prompt
    options = ClaudeAgentOptions(
        model=model or DEFAULT_MODEL,
        mcp_servers={"shader-tools": shader_server},
        allowed_tools=allowed_tools,
        system_prompt=EDIT_SYSTEM_PROMPT,
    )

    timer = get_timer()

    try:
        t_agent_start = time_mod.monotonic()
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)

            # Process the response
            async for message in client.receive_response():
                if verbose and hasattr(message, 'content'):
                    # Print text content for debugging
                    for block in getattr(message, 'content', []):
                        if hasattr(block, 'text'):
                            print(block.text)

        t_agent_total = time_mod.monotonic() - t_agent_start
        tool_time = sum(e["elapsed"] for e in timer.events)
        timer.record("claude agent (thinking + API)", t_agent_total - tool_time)

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
