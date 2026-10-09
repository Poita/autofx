// Parser for `// @param` comment lines, mirroring autofx/params.py.
// tests/param_cases.json holds the cases both implementations must agree on.
//
//   // @param <name> <type> <default> [min, max] "description"

export const GLSL_TYPES = {
  float: "float",
  int: "int",
  bool: "bool",
  color: "vec3",
  vec2: "vec2",
  vec3: "vec3",
};
const VECTOR_SIZES = { vec2: 2, vec3: 3 };
const RANGED_TYPES = new Set(["float", "int", "vec2", "vec3"]);
const RESERVED_NAMES = new Set(["iTime", "iResolution", "iSeed", "mainImage", "main", "fragColor"]);

const NUM = String.raw`[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?`;
const MARKER = /^\s*\/\/\s*@param\b/;
const LINE = new RegExp(
  String.raw`^(?<indent>\s*)\/\/\s*@param\s+(?<name>[A-Za-z_]\w*)\s+(?<type>\w+)\s+` +
    String.raw`(?<default>\([^)]*\)|#\w+|\S+)` +
    String.raw`(?:\s*\[\s*(?<min>${NUM})\s*,\s*(?<max>${NUM})\s*\])?` +
    String.raw`(?:\s*"(?<desc>[^"]*)")?\s*$`,
);
const NUMBER_ONLY = new RegExp(`^${NUM}$`);
const COLOR = /^#[0-9a-fA-F]{6}$/;

function number(text) {
  if (!NUMBER_ONLY.test(text.trim())) throw new Error(text);
  return Number(text);
}

function parseLine(m, line) {
  const { name, type } = m.groups;
  const raw = m.groups.default;
  const hasRange = m.groups.min !== undefined;
  if (!(type in GLSL_TYPES)) throw new Error(`unknown type '${type}'`);
  if (RESERVED_NAMES.has(name)) throw new Error(`'${name}' is reserved`);
  if (RANGED_TYPES.has(type) && !hasRange) throw new Error(`'${name}' needs a [min, max] range`);
  if (!RANGED_TYPES.has(type) && hasRange) throw new Error(`'${name}' (${type}) cannot have a range`);

  const lo = hasRange ? number(m.groups.min) : null;
  const hi = hasRange ? number(m.groups.max) : null;

  let def;
  if (type === "bool") {
    if (raw !== "true" && raw !== "false") throw new Error(`'${name}' (bool) default must be true or false`);
    def = raw === "true";
  } else if (type === "color") {
    if (!COLOR.test(raw)) throw new Error(`'${name}' (color) default must look like #rrggbb`);
    def = raw.toLowerCase();
  } else if (type in VECTOR_SIZES) {
    const size = VECTOR_SIZES[type];
    const parts = raw.startsWith("(") ? raw.slice(1, -1).split(",") : [];
    if (parts.length !== size) throw new Error(`'${name}' (${type}) default needs ${size} components`);
    def = parts.map(number);
  } else {
    def = number(raw);
  }

  if (type === "int" && ![def, lo, hi].every(Number.isInteger)) {
    throw new Error(`'${name}' (int) needs whole numbers`);
  }
  if (hasRange) {
    if (lo >= hi) throw new Error(`range min must be less than max for '${name}'`);
    const components = Array.isArray(def) ? def : [def];
    if (components.some((c) => c < lo || c > hi)) {
      throw new Error(`default for '${name}' is outside [${lo}, ${hi}]`);
    }
  }
  return { name, type, default: def, min: lo, max: hi, description: m.groups.desc ?? "", line };
}

// Returns { params, errors }; errors are "line N: ..." strings.
export function parseParams(source) {
  const params = [];
  const errors = [];
  const seen = new Set();
  source.split(/\r?\n/).forEach((text, i) => {
    const lineNo = i + 1;
    if (!MARKER.test(text)) return;
    const m = LINE.exec(text);
    try {
      if (!m) {
        throw new Error(
          'could not parse; expected // @param <name> <type> <default> [min, max] "description"',
        );
      }
      const param = parseLine(m, lineNo);
      if (seen.has(param.name)) throw new Error(`duplicate parameter '${param.name}'`);
      seen.add(param.name);
      params.push(param);
    } catch (e) {
      errors.push(`line ${lineNo}: ${e.message}`);
    }
  });
  return { params, errors };
}

export function uniformDeclarations(params) {
  return params.map((p) => `uniform ${GLSL_TYPES[p.type]} ${p.name};\n`).join("");
}

export function hexToRgb(hex) {
  return [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
}

// Trims float noise from sliders (0.30000000000000004 -> 0.3).
function tidy(n) {
  return Number(Number(n).toPrecision(6));
}

function formatFloat(n) {
  const s = String(tidy(n));
  return /[.eE]/.test(s) ? s : `${s}.0`;
}

export function formatValue(type, value) {
  if (type === "bool") return value ? "true" : "false";
  if (type === "color") return value.toLowerCase();
  if (type === "int") return String(Math.round(value));
  if (type in VECTOR_SIZES) return `(${value.map((v) => String(tidy(v))).join(", ")})`;
  return formatFloat(value);
}

// Rewrites the defaults of the given parameters, leaving every other line untouched.
export function setParamDefaults(source, values) {
  const lines = source.split("\n");
  for (const p of parseParams(source).params) {
    if (!(p.name in values)) continue;
    const indent = LINE.exec(lines[p.line - 1]).groups.indent;
    let text = `${indent}// @param ${p.name} ${p.type} ${formatValue(p.type, values[p.name])}`;
    if (p.min !== null) text += ` [${p.min}, ${p.max}]`;
    if (p.description) text += ` "${p.description}"`;
    lines[p.line - 1] = text;
  }
  return lines.join("\n");
}

// Duration, frame count, resolution and loop mode from the header the CLI writes.
export function renderSettings(source) {
  const settings = { duration: 1, frames: 10, loop: false, width: 256, height: 256 };
  const render = /^\/\/ Render with:(.*)$/m.exec(source)?.[1] ?? "";
  const generated = /^\/\/ Generated by:(.*)$/m.exec(source)?.[1] ?? "";
  const d = /\s-d\s+(\S+)/.exec(render);
  const f = /\s-f\s+(\d+)/.exec(render);
  const r = /\s-r\s+(\d+)x(\d+)/.exec(render);
  if (d) settings.duration = Number(d[1]);
  if (f) settings.frames = Number(f[1]);
  if (r) [settings.width, settings.height] = [Number(r[1]), Number(r[2])];
  settings.loop = /\s(--loop|-l)(\s|$)/.test(generated);
  return settings;
}
