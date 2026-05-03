"""
ModernGL-based shader renderer for Shadertoy-style GLSL shaders.

Renders fragment shaders to RGBA images with support for:
- iTime: Animation time in seconds
- iResolution: Viewport resolution (vec3)
- Transparent background support
"""

from typing import List, Tuple, Optional
import numpy as np
from PIL import Image

try:
    import moderngl
except ImportError:
    raise ImportError(
        "moderngl is required for shader rendering. "
        "Install it with: pip install moderngl"
    )


# Vertex shader for full-screen quad
VERTEX_SHADER = """
#version 330 core

in vec2 in_position;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
}
"""

# Fragment shader wrapper template
# The user's Shadertoy-style code is injected where {USER_SHADER} appears
FRAGMENT_SHADER_TEMPLATE = """
#version 330 core

uniform float iTime;
uniform vec3 iResolution;
uniform float iSeed;

out vec4 fragColor;

{USER_SHADER}

void main() {{
    mainImage(fragColor, gl_FragCoord.xy);
}}
"""


class ShaderRenderer:
    """
    Renders Shadertoy-style GLSL fragment shaders to images.

    Usage:
        renderer = ShaderRenderer(256, 256)
        frame = renderer.render(shader_code, time=0.5)
        renderer.cleanup()
    """

    def __init__(self, width: int, height: int):
        """
        Initialize the renderer with the given resolution.

        Args:
            width: Output image width in pixels
            height: Output image height in pixels
        """
        self.width = width
        self.height = height

        # Create standalone OpenGL context (no window required).
        # Backend selection:
        #   - MODERNGL_BACKEND env var if set (override)
        #   - 'egl' on Linux (works on headless servers via Mesa surfaceless;
        #     moderngl's default standalone init tries X11 first, which fails
        #     with `XOpenDisplay: cannot open display` on a server with no X)
        #   - default elsewhere (cgl on macOS, wgl on Windows)
        import os
        import sys
        backend = os.environ.get("MODERNGL_BACKEND")
        if backend:
            self.ctx = moderngl.create_context(standalone=True, backend=backend)
        elif sys.platform.startswith("linux"):
            self.ctx = moderngl.create_context(standalone=True, backend="egl")
        else:
            self.ctx = moderngl.create_standalone_context()

        # Create framebuffer for offscreen rendering
        self.fbo = self.ctx.framebuffer(
            color_attachments=[
                self.ctx.texture((width, height), 4)  # RGBA texture
            ]
        )

        # Full-screen quad vertices (two triangles)
        vertices = np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0, -1.0,
             1.0,  1.0,
            -1.0,  1.0,
        ], dtype='f4')

        self.vbo = self.ctx.buffer(vertices)
        self.program = None
        self.vao = None

    def compile_shader(self, shader_code: str) -> Tuple[bool, Optional[str]]:
        """
        Compile a Shadertoy-style shader.

        Args:
            shader_code: The user's shader code containing mainImage function

        Returns:
            Tuple of (success, error_message)
        """
        # Build the full fragment shader
        fragment_shader = FRAGMENT_SHADER_TEMPLATE.replace("{USER_SHADER}", shader_code)

        try:
            self.program = self.ctx.program(
                vertex_shader=VERTEX_SHADER,
                fragment_shader=fragment_shader,
            )

            # Create vertex array object
            self.vao = self.ctx.vertex_array(
                self.program,
                [(self.vbo, '2f', 'in_position')]
            )

            return True, None

        except Exception as e:
            error_msg = str(e)
            # Try to extract useful error info
            return False, error_msg

    def render(self, shader_code: str, time: float, seed: float = 0.0) -> Image.Image:
        """
        Render the shader at a specific time value.

        Args:
            shader_code: The user's shader code containing mainImage function
            time: The iTime value to use (seconds)
            seed: The iSeed value for procedural variation (default: 0.0)

        Returns:
            PIL Image in RGBA mode

        Raises:
            RuntimeError: If shader compilation fails
        """
        # Compile if needed or if shader changed
        if self.program is None:
            success, error = self.compile_shader(shader_code)
            if not success:
                raise RuntimeError(f"Shader compilation failed: {error}")

        # Set uniforms
        if 'iTime' in self.program:
            self.program['iTime'].value = time
        if 'iResolution' in self.program:
            self.program['iResolution'].value = (
                float(self.width),
                float(self.height),
                1.0  # pixel aspect ratio
            )
        if 'iSeed' in self.program:
            self.program['iSeed'].value = seed

        # Render to framebuffer
        self.fbo.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)  # Clear with transparent black
        self.vao.render()

        # Read pixels
        data = self.fbo.color_attachments[0].read()

        # Convert to PIL Image (need to flip vertically)
        image = Image.frombytes('RGBA', (self.width, self.height), data)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        return image

    def render_animation(
        self,
        shader_code: str,
        duration: float,
        num_frames: int,
        seed: float = 0.0
    ) -> List[Image.Image]:
        """
        Render an animation as a sequence of frames.

        Args:
            shader_code: The user's shader code containing mainImage function
            duration: Total animation duration in seconds
            num_frames: Number of frames to render
            seed: The iSeed value for procedural variation (default: 0.0)

        Returns:
            List of PIL Images in RGBA mode
        """
        # Compile the shader once
        success, error = self.compile_shader(shader_code)
        if not success:
            raise RuntimeError(f"Shader compilation failed: {error}")

        frames = []
        for i in range(num_frames):
            # Calculate time for this frame
            # We want the animation to span from 0 to duration
            time = (i / max(num_frames - 1, 1)) * duration

            # Render the frame (shader already compiled)
            frame = self.render(shader_code, time, seed)
            frames.append(frame)

        return frames

    def cleanup(self):
        """Release OpenGL resources."""
        if self.vao:
            self.vao.release()
        if self.program:
            self.program.release()
        if self.vbo:
            self.vbo.release()
        if self.fbo:
            self.fbo.release()
        if self.ctx:
            self.ctx.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


def render_shader(
    shader_code: str,
    duration: float,
    resolution: Tuple[int, int],
    num_frames: int,
    seed: float = 0.0
) -> List[Image.Image]:
    """
    Convenience function to render a shader animation.

    Args:
        shader_code: Shadertoy-style GLSL code with mainImage function
        duration: Animation duration in seconds
        resolution: (width, height) tuple
        num_frames: Number of frames to generate
        seed: The iSeed value for procedural variation (default: 0.0)

    Returns:
        List of PIL Images in RGBA mode
    """
    width, height = resolution

    with ShaderRenderer(width, height) as renderer:
        return renderer.render_animation(shader_code, duration, num_frames, seed)


def compile_shader(shader_code: str, width: int = 256, height: int = 256) -> Tuple[bool, Optional[str]]:
    """
    Test if a shader compiles successfully.

    Args:
        shader_code: Shadertoy-style GLSL code with mainImage function
        width: Test resolution width
        height: Test resolution height

    Returns:
        Tuple of (success, error_message)
    """
    try:
        with ShaderRenderer(width, height) as renderer:
            return renderer.compile_shader(shader_code)
    except Exception as e:
        return False, str(e)
