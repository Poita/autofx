import json
from dataclasses import asdict
from pathlib import Path

import pytest

from autofx.params import parse_params, uniform_declarations, uniform_values

CASES = json.loads((Path(__file__).parent / "param_cases.json").read_text())


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda c: c["name"])
def test_parses_valid_params(case):
    params, errors = parse_params(case["source"])
    assert errors == []
    assert [asdict(p) for p in params] == pytest.approx(case["params"])


@pytest.mark.parametrize("case", CASES["invalid"], ids=lambda c: c["name"])
def test_reports_invalid_params(case):
    _, errors = parse_params(case["source"])
    assert any(case["error"] in e for e in errors), errors


def test_uniform_declarations_map_color_to_vec3():
    params, _ = parse_params(
        "// @param speed float 1 [0, 2]\n// @param tint color #ff0000\n// @param n int 3 [1, 9]"
    )
    assert uniform_declarations(params) == (
        "uniform float speed;\nuniform vec3 tint;\nuniform int n;\n"
    )


def test_uniform_values_use_defaults_and_convert_colors():
    params, _ = parse_params("// @param tint color #ff8000\n// @param on bool true")
    values = uniform_values(params)
    assert values["tint"] == pytest.approx((1.0, 128 / 255, 0.0))
    assert values["on"] is True


def test_uniform_values_apply_overrides():
    params, _ = parse_params("// @param speed float 1 [0, 4]")
    assert uniform_values(params, {"speed": 3.0}) == {"speed": 3.0}
