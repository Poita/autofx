"""
Tweakable shader parameters declared in comments.

A parameter is one comment line in the shader source:

    // @param <name> <type> <default> [min, max] "description"

Types and default syntax:
    float   1.5                 range required
    int     24                  range required, whole numbers
    bool    true | false        no range
    color   #ffb547             no range, becomes a vec3 (0-1 RGB)
    vec2    (0.2, -0.5)         range required, applies to every component
    vec3    (1, 0.5, 0.25)      range required, applies to every component

The description is optional. The renderer declares a uniform for every
parameter, so the shader uses the name directly without declaring it.

This grammar is mirrored in autofx/editor/params.js; tests/param_cases.json
holds the shared cases both parsers must agree on.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

GLSL_TYPES = {
    "float": "float",
    "int": "int",
    "bool": "bool",
    "color": "vec3",
    "vec2": "vec2",
    "vec3": "vec3",
}
VECTOR_SIZES = {"vec2": 2, "vec3": 3}
RANGED_TYPES = {"float", "int", "vec2", "vec3"}
RESERVED_NAMES = {"iTime", "iResolution", "iSeed", "mainImage", "main", "fragColor"}

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_MARKER = re.compile(r"^\s*//\s*@param\b")
_LINE = re.compile(
    r"^\s*//\s*@param\s+(?P<name>[A-Za-z_]\w*)\s+(?P<type>\w+)\s+"
    r"(?P<default>\([^)]*\)|#\w+|\S+)"
    rf"(?:\s*\[\s*(?P<min>{_NUM})\s*,\s*(?P<max>{_NUM})\s*\])?"
    r"(?:\s*\"(?P<desc>[^\"]*)\")?\s*$"
)
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

Value = Union[float, int, bool, str, List[float]]


@dataclass
class Param:
    name: str
    type: str
    default: Value
    min: Optional[float]
    max: Optional[float]
    description: str
    line: int


def _number(text: str) -> float:
    if not re.fullmatch(_NUM, text.strip()):
        raise ValueError(text)
    value = float(text)
    return int(value) if value.is_integer() else value


def _parse_line(match: "re.Match", line: int) -> Param:
    name, ptype = match["name"], match["type"]
    raw = match["default"]
    has_range = match["min"] is not None
    if ptype not in GLSL_TYPES:
        raise ValueError(f"unknown type '{ptype}'")
    if name in RESERVED_NAMES:
        raise ValueError(f"'{name}' is reserved")
    if ptype in RANGED_TYPES and not has_range:
        raise ValueError(f"'{name}' needs a [min, max] range")
    if ptype not in RANGED_TYPES and has_range:
        raise ValueError(f"'{name}' ({ptype}) cannot have a range")

    lo = _number(match["min"]) if has_range else None
    hi = _number(match["max"]) if has_range else None

    if ptype == "bool":
        if raw not in ("true", "false"):
            raise ValueError(f"'{name}' (bool) default must be true or false")
        default: Value = raw == "true"
    elif ptype == "color":
        if not _COLOR.match(raw):
            raise ValueError(f"'{name}' (color) default must look like #rrggbb")
        default = raw.lower()
    elif ptype in VECTOR_SIZES:
        size = VECTOR_SIZES[ptype]
        parts = raw.strip("()").split(",") if raw.startswith("(") else []
        if len(parts) != size:
            raise ValueError(f"'{name}' ({ptype}) default needs {size} components")
        default = [_number(p) for p in parts]
    else:
        default = _number(raw)

    if ptype == "int" and not all(isinstance(v, int) for v in (default, lo, hi)):
        raise ValueError(f"'{name}' (int) needs whole numbers")
    if has_range:
        if lo >= hi:
            raise ValueError(f"range min must be less than max for '{name}'")
        components = default if isinstance(default, list) else [default]
        if any(not lo <= c <= hi for c in components):
            raise ValueError(f"default for '{name}' is outside [{lo}, {hi}]")

    return Param(name, ptype, default, lo, hi, match["desc"] or "", line)


def parse_params(source: str) -> Tuple[List[Param], List[str]]:
    """Parse every `// @param` line. Returns (params, errors); errors are "line N: ..." strings."""
    params: List[Param] = []
    errors: List[str] = []
    seen = set()
    for number, text in enumerate(source.splitlines(), start=1):
        if not _MARKER.match(text):
            continue
        match = _LINE.match(text)
        try:
            if not match:
                raise ValueError("could not parse; expected "
                                 '// @param <name> <type> <default> [min, max] "description"')
            param = _parse_line(match, number)
            if param.name in seen:
                raise ValueError(f"duplicate parameter '{param.name}'")
        except ValueError as e:
            errors.append(f"line {number}: {e}")
            continue
        seen.add(param.name)
        params.append(param)
    return params, errors


def uniform_declarations(params: List[Param]) -> str:
    """GLSL uniform declarations for the given parameters."""
    return "".join(f"uniform {GLSL_TYPES[p.type]} {p.name};\n" for p in params)


def hex_to_rgb(color: str) -> Tuple[float, float, float]:
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def uniform_values(params: List[Param], overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Uniform values for the parameters: overrides where given, defaults otherwise."""
    overrides = overrides or {}
    values = {}
    for p in params:
        value = overrides.get(p.name, p.default)
        if p.type == "color" and isinstance(value, str):
            value = hex_to_rgb(value)
        elif isinstance(value, list):
            value = tuple(float(v) for v in value)
        elif p.type == "float":
            value = float(value)
        values[p.name] = value
    return values
