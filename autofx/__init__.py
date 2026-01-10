"""
AutoFX - AI-powered visual effects animation generator.

This package uses Claude to generate Shadertoy-style GLSL shaders
and renders them to animated GIFs with transparent backgrounds.

Usage:
    # High-level API (uses Claude Agent)
    from autofx import generate_vfx

    result = await generate_vfx(
        prompt="fiery explosion",
        duration=1.0,
        resolution=(256, 256),
        frames=10,
        output_path="explosion.gif"
    )

    # Low-level API (direct shader rendering)
    from autofx import render_shader, save_gif

    shader_code = '''
    void mainImage(out vec4 fragColor, in vec2 fragCoord) {
        vec2 uv = fragCoord / iResolution.xy;
        float t = iTime;
        fragColor = vec4(uv, 0.5 + 0.5 * sin(t), 1.0);
    }
    '''

    frames = render_shader(shader_code, duration=1.0, resolution=(256, 256), num_frames=10)
    save_gif(frames, "output.gif", duration=1.0)
"""

__version__ = "0.1.0"

# High-level API
from .agent import generate_vfx, generate_vfx_with_feedback

# Low-level rendering API
from .renderer import (
    render_shader,
    compile_shader,
    ShaderRenderer,
)

# GIF export
from .gif import (
    save_gif,
    frame_to_base64_png,
    frames_to_base64_gif,
)

__all__ = [
    # Version
    "__version__",
    # High-level API
    "generate_vfx",
    "generate_vfx_with_feedback",
    # Low-level API
    "render_shader",
    "compile_shader",
    "ShaderRenderer",
    # GIF utilities
    "save_gif",
    "frame_to_base64_png",
    "frames_to_base64_gif",
]
