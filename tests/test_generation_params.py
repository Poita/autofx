from autofx.agent import EDIT_SYSTEM_PROMPT, SYSTEM_PROMPT
from autofx.tools import describe_compile_result


def test_system_prompts_describe_the_param_dsl():
    for prompt in (SYSTEM_PROMPT, EDIT_SYSTEM_PROMPT):
        assert '// @param <name> <type> <default> [min, max] "description"' in prompt


def test_compile_result_lists_parsed_params():
    text = describe_compile_result(
        '// @param speed float 1.5 [0.1, 4] "Animation speed"\n'
        "// @param core color #ffb547\n",
        True,
        None,
    )
    assert "compiled successfully" in text
    assert "speed (float) = 1.5 in [0.1, 4]: Animation speed" in text
    assert "core (color) = #ffb547" in text


def test_compile_result_warns_when_there_are_no_params():
    text = describe_compile_result("void mainImage(out vec4 c, in vec2 p) {}", True, None)
    assert "No tweakable parameters" in text


def test_compile_result_passes_errors_through():
    text = describe_compile_result("", False, "ERROR: 0:12: syntax error")
    assert "compilation failed" in text
    assert "ERROR: 0:12: syntax error" in text
