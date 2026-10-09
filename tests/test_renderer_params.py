import pytest

pytest.importorskip("moderngl")

from autofx.renderer import ShaderRenderer, compile_shader, render_shader

TINT_SHADER = """
// @param tint color #ff8000 "Fill color"
// @param strength float 1.0 [0, 1] "Brightness"
// @param unused int 3 [1, 9]
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    fragColor = vec4(tint * strength, 1.0);
}
"""


def test_params_render_with_their_defaults():
    with ShaderRenderer(4, 4) as renderer:
        pixel = renderer.render(TINT_SHADER, 0.0).getpixel((1, 1))
    assert pixel == (255, 128, 0, 255)


def test_param_overrides_change_the_render():
    frames = render_shader(TINT_SHADER, 1.0, (4, 4), 2, params={"strength": 0.5})
    r, g, b, a = frames[0].getpixel((1, 1))
    assert (r, b, a) == (128, 0, 255)
    assert g in (64, 65)


def test_invalid_param_line_fails_compilation_with_line_number():
    ok, error = compile_shader("// @param size float 9 [0, 2]\n" + TINT_SHADER)
    assert not ok
    assert "line 1: default for 'size' is outside [0, 2]" in error
