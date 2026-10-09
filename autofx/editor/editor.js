// AutoFX shader editor: live WebGL2 preview of Shadertoy-style shaders with
// controls generated from their `// @param` lines.
//
// Sources, in order of preference:
//   - the `autofx editor` server (/api/shaders): list, load and save shaders
//   - a static shaders.json manifest next to this page: list and load only
//   - files opened or dropped by the user

import {
  parseParams,
  uniformDeclarations,
  setParamDefaults,
  renderSettings,
  hexToRgb,
} from "./params.js";

const $ = (id) => document.getElementById(id);
const el = {
  title: $("title"), status: $("status"), toast: $("toast"),
  openBtn: $("open-btn"), openFile: $("open-file"),
  copyBtn: $("copy-btn"), downloadBtn: $("download-btn"),
  saveBtn: $("save-btn"), saveAsBtn: $("saveas-btn"),
  saveAsForm: $("saveas-form"), saveAsName: $("saveas-name"), saveAsCancel: $("saveas-cancel"),
  filter: $("filter"), list: $("shader-list"),
  stage: $("stage"), canvas: $("canvas"), drop: $("drop"), glError: $("glerror"),
  prev: $("prev-btn"), play: $("play-btn"), next: $("next-btn"),
  scrub: $("scrub"), time: $("time"), duration: $("duration"), rate: $("rate"),
  seed: $("seed"), bg: $("bg"), res: $("res"),
  code: $("code"), gutter: $("gutter"), errors: $("errors"), compileInfo: $("compile-info"),
  paramCount: $("param-count"), paramList: $("param-list"),
  randomize: $("randomize-btn"), resetAll: $("reset-all-btn"),
};

const state = {
  source: "none",          // "server" | "static" | "none"
  writable: false,
  shaders: [],             // paths offered in the sidebar
  docs: new Map(),         // path -> { saved, code, values } so switching keeps edits
  path: null,              // current document key
  name: "",
  saved: "",               // text last loaded or saved
  params: [],
  values: {},
  settings: renderSettings(""),
  playing: true,
  t: 0,
  rate: 1,
  seed: 0,
  errors: [],
};

// ---------------------------------------------------------------- WebGL

const gl = el.canvas.getContext("webgl2", { premultipliedAlpha: false, alpha: true, antialias: false });
const VERTEX = `#version 300 es
in vec2 position;
void main() { gl_Position = vec4(position, 0.0, 1.0); }`;

let program = null;        // last program that compiled; kept while the code has errors
let locations = {};
let programParams = [];

if (gl) {
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
} else {
  el.glError.hidden = false;
  el.glError.textContent = "This browser has no WebGL2 support, so shaders can't be previewed.";
}

function fragmentPrefix(params) {
  return `#version 300 es
precision highp float;
precision highp int;
uniform float iTime;
uniform vec3 iResolution;
uniform float iSeed;
${uniformDeclarations(params)}out vec4 fragColor;
`;
}

function compileStage(type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader) || "unknown compile error";
    gl.deleteShader(shader);
    throw new Error(log);
  }
  return shader;
}

// Maps "ERROR: 0:57: message" lines from the driver back to lines in the user's code.
function mapGlErrors(log, prefixLines, codeLines) {
  const errors = [];
  for (const raw of log.split("\n")) {
    const text = raw.trim();
    if (!text) continue;
    const m = /^(?:ERROR|WARNING):\s*\d+:(\d+):\s*(.*)$/.exec(text);
    if (!m) { errors.push({ line: null, message: text }); continue; }
    const line = Number(m[1]) - prefixLines;
    errors.push(line >= 1 && line <= codeLines
      ? { line, message: m[2] }
      : { line: null, message: m[2] });
  }
  return errors;
}

function compile(code) {
  const { params, errors } = parseParams(code);
  if (errors.length) {
    return { params, errors: errors.map((e) => {
      const m = /^line (\d+): (.*)$/.exec(e);
      return { line: Number(m[1]), message: `@param: ${m[2]}` };
    }) };
  }
  if (!gl) return { params, errors: [] };

  const prefix = fragmentPrefix(params);
  const prefixLines = prefix.split("\n").length - 1;
  const fragment = `${prefix}${code}\nvoid main() { mainImage(fragColor, gl_FragCoord.xy); }\n`;
  const started = performance.now();
  let vs, fs;
  try {
    vs = compileStage(gl.VERTEX_SHADER, VERTEX);
    fs = compileStage(gl.FRAGMENT_SHADER, fragment);
  } catch (e) {
    if (vs) gl.deleteShader(vs);
    return { params, errors: mapGlErrors(e.message, prefixLines, code.split("\n").length) };
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, vs);
  gl.attachShader(prog, fs);
  gl.bindAttribLocation(prog, 0, "position");
  gl.linkProgram(prog);
  gl.deleteShader(vs);
  gl.deleteShader(fs);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
    const log = gl.getProgramInfoLog(prog) || "link failed";
    gl.deleteProgram(prog);
    return { params, errors: [{ line: null, message: log }] };
  }

  if (program) gl.deleteProgram(program);
  program = prog;
  programParams = params;
  locations = {};
  for (const name of ["iTime", "iResolution", "iSeed", ...params.map((p) => p.name)]) {
    locations[name] = gl.getUniformLocation(prog, name);
  }
  el.compileInfo.textContent = `compiled in ${(performance.now() - started).toFixed(0)} ms`;
  return { params, errors: [] };
}

function setUniform(p, value) {
  const loc = locations[p.name];
  if (!loc) return; // unused uniforms are compiled away
  switch (p.type) {
    case "float": gl.uniform1f(loc, value); break;
    case "int": gl.uniform1i(loc, Math.round(value)); break;
    case "bool": gl.uniform1i(loc, value ? 1 : 0); break;
    case "color": gl.uniform3fv(loc, hexToRgb(value)); break;
    case "vec2": gl.uniform2fv(loc, value); break;
    case "vec3": gl.uniform3fv(loc, value); break;
  }
}

function draw() {
  if (!gl || !program) return;
  const { width, height } = el.canvas;
  gl.viewport(0, 0, width, height);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.useProgram(program);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  if (locations.iTime) gl.uniform1f(locations.iTime, Math.min(state.t, state.settings.duration));
  if (locations.iResolution) gl.uniform3f(locations.iResolution, width, height, 1);
  if (locations.iSeed) gl.uniform1f(locations.iSeed, state.seed);
  for (const p of programParams) {
    setUniform(p, p.name in state.values ? state.values[p.name] : p.default);
  }
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}

// ---------------------------------------------------------------- playback

// One-shot effects hold their (empty) last frame briefly so the ending is visible.
const ONE_SHOT_HOLD = 0.35;
let lastFrame = performance.now();

function cycleLength() {
  const d = state.settings.duration;
  return state.settings.loop ? d : d + ONE_SHOT_HOLD;
}

function frameTime(i) {
  const { frames, duration } = state.settings;
  return (i / Math.max(frames - 1, 1)) * duration;
}

function currentFrame() {
  const { frames, duration } = state.settings;
  return Math.round((Math.min(state.t, duration) / duration) * Math.max(frames - 1, 1));
}

function updateTimeUi() {
  const d = state.settings.duration;
  const t = Math.min(state.t, d);
  el.scrub.max = String(d);
  el.scrub.step = String(d / 1000);
  if (document.activeElement !== el.scrub) el.scrub.value = String(t);
  el.time.textContent =
    `${t.toFixed(2)} / ${d.toFixed(2)}s · frame ${currentFrame() + 1}/${state.settings.frames}`;
}

function tick(now) {
  const dt = Math.min((now - lastFrame) / 1000, 0.1);
  lastFrame = now;
  if (state.playing) {
    state.t = (state.t + dt * state.rate) % cycleLength();
  }
  draw();
  updateTimeUi();
  requestAnimationFrame(tick);
}

function setPlaying(playing) {
  state.playing = playing;
  el.play.textContent = playing ? "❚❚" : "▶";
  el.play.setAttribute("aria-label", playing ? "Pause" : "Play");
}

function stepFrame(delta) {
  setPlaying(false);
  const { frames } = state.settings;
  const i = (currentFrame() + delta + frames) % frames;
  state.t = frameTime(i);
}

function applyResolution() {
  const scale = Number(el.res.value);
  el.canvas.width = state.settings.width * scale;
  el.canvas.height = state.settings.height * scale;
  el.canvas.style.aspectRatio = `${state.settings.width} / ${state.settings.height}`;
}

// ---------------------------------------------------------------- documents

function currentCode() {
  return el.code.value;
}

function textToSave() {
  return setParamDefaults(currentCode(), state.values);
}

function isDirty() {
  return state.path !== null && textToSave() !== state.saved;
}

function storeDoc() {
  if (state.path === null) return;
  state.docs.set(state.path, {
    saved: state.saved, code: currentCode(), values: { ...state.values },
    name: state.name, writable: state.docs.get(state.path)?.writable ?? false,
  });
}

function openDoc(path, text, { name, writable }) {
  storeDoc();
  const existing = state.docs.get(path);
  state.path = path;
  state.name = name;
  state.saved = existing ? existing.saved : text;
  el.code.value = existing ? existing.code : text;
  state.values = existing ? { ...existing.values } : {};
  state.docs.set(path, { saved: state.saved, code: el.code.value, values: state.values, name, writable });

  state.settings = renderSettings(el.code.value);
  el.duration.value = String(state.settings.duration);
  state.t = 0;
  applyResolution();
  state.params = [];
  recompile({ mode: existing ? "restore" : "reset" });
  el.code.scrollTop = 0;
  if (state.source === "server" && writable) history.replaceState(null, "", `#${encodeURIComponent(path)}`);
  renderList();
  updateChrome();
}

async function loadShader(path) {
  try {
    const url = state.source === "server" ? `/api/shader?path=${encodeURIComponent(path)}` : path;
    const resp = await fetch(url, { cache: "no-store" });
    if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
    openDoc(path, await resp.text(), { name: path, writable: state.writable });
  } catch (e) {
    toast(`Couldn't load ${path}: ${e.message}`);
  }
}

function openLocalFile(file) {
  file.text().then((text) => {
    openDoc(`local:${file.name}`, text, { name: file.name, writable: false });
    toast(`Opened ${file.name}`);
  });
}

// ---------------------------------------------------------------- compile + params

let compileTimer = 0;

// mode: "edit" (code changed), "reset" (fresh document) or "restore" (reopened document).
function recompile({ mode = "edit" } = {}) {
  const previous = state.params;
  const result = compile(currentCode());
  state.errors = result.errors;
  reconcileValues(previous, result.params, mode);
  state.params = result.params;
  renderParams();
  renderErrors();
  renderGutter();
  updateChrome();
}

// Keeps tweaked values across code edits. A value that still equals its old
// default follows the new default; other values are kept (clamped to range).
// A reopened document keeps the values stored with it.
function reconcileValues(previous, next, mode) {
  const old = new Map(previous.map((p) => [p.name, p]));
  const values = {};
  for (const p of next) {
    if (mode === "reset" || !(p.name in state.values)) continue;
    const value = state.values[p.name];
    if (mode === "edit") {
      const before = old.get(p.name);
      if (!before || before.type !== p.type || sameValue(value, before.default)) continue;
    } else if (!sameShape(p, value)) {
      continue;
    }
    values[p.name] = clampValue(p, value);
  }
  state.values = values;
}

function sameShape(p, value) {
  if (p.type === "vec2" || p.type === "vec3") return Array.isArray(value) && value.length === p.default.length;
  return typeof value === typeof p.default;
}

function sameValue(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function clampValue(p, value) {
  if (p.min === null) return value;
  const clamp = (v) => Math.min(p.max, Math.max(p.min, v));
  return Array.isArray(value) ? value.map(clamp) : clamp(value);
}

function valueOf(p) {
  return p.name in state.values ? state.values[p.name] : p.default;
}

function setValue(p, value, row) {
  if (sameValue(value, p.default)) delete state.values[p.name];
  else state.values[p.name] = value;
  row.classList.toggle("is-changed", p.name in state.values);
  updateChrome();
}

function niceStep(p) {
  if (p.type === "int") return 1;
  const span = p.max - p.min;
  const raw = span / 500;
  const pow = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map((m) => m * pow).find((s) => s >= raw);
}

function formatNumber(p, v) {
  if (p.type === "int") return String(Math.round(v));
  const decimals = Math.max(0, Math.min(4, -Math.floor(Math.log10(niceStep(p)))));
  return Number(v).toFixed(decimals);
}

function makeNumberControl(p, axis, get, set) {
  const wrap = document.createElement("div");
  wrap.className = "ctl";
  const label = document.createElement("span");
  label.className = "axis";
  label.textContent = axis;
  const range = document.createElement("input");
  range.type = "range";
  range.min = String(p.min);
  range.max = String(p.max);
  range.step = String(niceStep(p));
  range.setAttribute("aria-label", axis ? `${p.name} ${axis}` : p.name);
  const num = document.createElement("input");
  num.type = "number";
  num.min = String(p.min);
  num.max = String(p.max);
  num.step = range.step;
  num.setAttribute("aria-label", `${p.name}${axis ? ` ${axis}` : ""} value`);
  const sync = () => { range.value = String(get()); num.value = formatNumber(p, get()); };
  range.addEventListener("input", () => { set(Number(range.value)); num.value = formatNumber(p, get()); });
  num.addEventListener("change", () => {
    const v = Number(num.value);
    if (Number.isFinite(v)) set(clampValue(p, p.type === "int" ? Math.round(v) : v));
    sync();
  });
  wrap.append(label, range, num);
  sync();
  return { node: wrap, sync };
}

function renderParams() {
  const params = state.params;
  el.paramCount.textContent = params.length ? `Parameters · ${params.length}` : "Parameters";
  el.randomize.disabled = el.resetAll.disabled = !params.length;
  el.paramList.replaceChildren();

  if (!params.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.innerHTML = state.path === null
      ? "Open a shader to see its parameters."
      : "This shader has no tweakable parameters. Add lines like these to the code:" +
        "<code>// @param speed float 1.0 [0.1, 4.0] \"Animation speed\"\n// @param tint color #ffb547 \"Main color\"</code>";
    el.paramList.append(empty);
    return;
  }

  for (const p of params) {
    const row = document.createElement("div");
    row.className = "param";
    row.classList.toggle("is-changed", p.name in state.values);

    const top = document.createElement("div");
    top.className = "top";
    const dot = document.createElement("span");
    dot.className = "changed";
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = p.name;
    const type = document.createElement("span");
    type.className = "type";
    type.textContent = p.type;
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "reset";
    reset.textContent = "↺ reset";
    reset.title = "Reset to default";
    top.append(dot, name, type, reset);
    row.append(top);

    if (p.description) {
      const desc = document.createElement("div");
      desc.className = "desc";
      desc.textContent = p.description;
      row.append(desc);
    }

    const syncs = [];
    if (p.type === "float" || p.type === "int") {
      const c = makeNumberControl(p, "", () => valueOf(p), (v) => setValue(p, v, row));
      row.append(c.node);
      syncs.push(c.sync);
    } else if (p.type === "vec2" || p.type === "vec3") {
      ["x", "y", "z"].slice(0, p.type === "vec2" ? 2 : 3).forEach((axis, i) => {
        const c = makeNumberControl(p, axis, () => valueOf(p)[i], (v) => {
          const next = [...valueOf(p)];
          next[i] = v;
          setValue(p, next, row);
        });
        row.append(c.node);
        syncs.push(c.sync);
      });
    } else if (p.type === "color") {
      const wrap = document.createElement("div");
      wrap.className = "ctl color";
      const picker = document.createElement("input");
      picker.type = "color";
      picker.setAttribute("aria-label", p.name);
      const hex = document.createElement("input");
      hex.type = "text";
      hex.spellcheck = false;
      hex.setAttribute("aria-label", `${p.name} hex value`);
      const sync = () => { picker.value = valueOf(p); hex.value = valueOf(p); };
      picker.addEventListener("input", () => { setValue(p, picker.value.toLowerCase(), row); hex.value = valueOf(p); });
      hex.addEventListener("change", () => {
        const v = hex.value.trim().replace(/^([0-9a-f]{6})$/i, "#$1").toLowerCase();
        if (/^#[0-9a-f]{6}$/.test(v)) setValue(p, v, row);
        sync();
      });
      wrap.append(picker, hex);
      row.append(wrap);
      sync();
      syncs.push(sync);
    } else if (p.type === "bool") {
      const label = document.createElement("label");
      label.className = "switch";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = valueOf(p);
      box.addEventListener("change", () => setValue(p, box.checked, row));
      label.append(box, document.createTextNode("Enabled"));
      row.append(label);
      syncs.push(() => { box.checked = valueOf(p); });
    }

    reset.addEventListener("click", () => {
      delete state.values[p.name];
      row.classList.remove("is-changed");
      syncs.forEach((s) => s());
      updateChrome();
    });
    row.syncAll = () => syncs.forEach((s) => s());
    el.paramList.append(row);
  }
}

function randomValue(p) {
  const r = (lo, hi) => lo + Math.random() * (hi - lo);
  switch (p.type) {
    case "float": return Number(r(p.min, p.max).toPrecision(4));
    case "int": return Math.round(r(p.min, p.max));
    case "bool": return Math.random() < 0.5;
    case "color": return "#" + Array.from({ length: 3 }, () =>
      Math.floor(Math.random() * 256).toString(16).padStart(2, "0")).join("");
    default: return p.default.map(() => Number(r(p.min, p.max).toPrecision(4)));
  }
}

// ---------------------------------------------------------------- editor chrome

function renderGutter() {
  const count = el.code.value.split("\n").length;
  const bad = new Set(state.errors.map((e) => e.line).filter(Boolean));
  const parts = [];
  for (let i = 1; i <= count; i++) parts.push(bad.has(i) ? `<span class="err">${i}</span>` : String(i));
  el.gutter.innerHTML = parts.join("\n");
  el.gutter.scrollTop = el.code.scrollTop;
}

function renderErrors() {
  el.errors.replaceChildren(...state.errors.map((e) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = e.line ? `line ${e.line}: ${e.message}` : e.message;
    if (e.line) b.addEventListener("click", () => goToLine(e.line));
    li.append(b);
    return li;
  }));
}

function goToLine(line) {
  const lines = el.code.value.split("\n");
  const start = lines.slice(0, line - 1).reduce((n, l) => n + l.length + 1, 0);
  el.code.focus();
  el.code.setSelectionRange(start, start + (lines[line - 1] ?? "").length);
  const lineHeight = parseFloat(getComputedStyle(el.code).lineHeight);
  el.code.scrollTop = Math.max(0, (line - 4) * lineHeight);
}

function renderList() {
  const query = el.filter.value.trim().toLowerCase();
  const items = [];
  let lastDir = null;
  const paths = state.shaders.filter((p) => p.toLowerCase().includes(query));
  for (const path of paths) {
    const slash = path.lastIndexOf("/");
    const dir = slash >= 0 ? path.slice(0, slash) : "";
    if (dir !== lastDir) {
      if (dir) {
        const li = document.createElement("li");
        li.className = "dir";
        li.textContent = dir + "/";
        items.push(li);
      }
      lastDir = dir;
    }
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button";
    const dot = document.createElement("span");
    dot.className = "dot";
    b.append(dot, document.createTextNode(path.slice(slash + 1)));
    b.title = path;
    b.setAttribute("aria-current", String(path === state.path));
    const doc = state.docs.get(path);
    const dirty = path === state.path ? isDirty()
      : doc && setParamDefaults(doc.code, doc.values) !== doc.saved;
    b.classList.toggle("dirty", Boolean(dirty));
    b.addEventListener("click", () => { if (path !== state.path) loadShader(path); });
    li.append(b);
    items.push(li);
  }
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = state.source === "none"
      ? "Open or drop a .glsl file. Run `autofx editor <folder>` to browse and save shaders."
      : "No shaders match.";
    items.push(li);
  }
  el.list.replaceChildren(...items);
}

function updateChrome() {
  const loaded = state.path !== null;
  const doc = loaded ? state.docs.get(state.path) : null;
  const canSave = loaded && state.source === "server" && doc?.writable;
  const dirty = isDirty();

  el.title.innerHTML = "";
  if (loaded) {
    const b = document.createElement("b");
    b.textContent = state.name;
    el.title.append(b, document.createTextNode(
      ` · ${state.settings.loop ? "loop" : "one-shot"} · ${state.settings.width}×${state.settings.height}`));
  } else {
    el.title.textContent = "No shader loaded";
  }

  el.status.hidden = !loaded;
  el.status.className = "status";
  if (state.errors.length) {
    el.status.classList.add("error");
    el.status.textContent = `${state.errors.length} error${state.errors.length > 1 ? "s" : ""}`;
  } else if (dirty) {
    el.status.classList.add("dirty");
    el.status.textContent = "unsaved changes";
  } else {
    el.status.classList.add("ok");
    el.status.textContent = canSave ? "saved" : "compiled";
  }

  el.copyBtn.disabled = el.downloadBtn.disabled = !loaded;
  el.saveBtn.hidden = el.saveAsBtn.hidden = state.source !== "server";
  el.saveBtn.disabled = !canSave || !dirty;
  el.saveAsBtn.disabled = !loaded;

  const current = el.list.querySelector('[aria-current="true"]');
  if (current) current.classList.toggle("dirty", dirty);
}

let toastTimer = 0;
function toast(message) {
  el.toast.textContent = message;
  el.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.toast.hidden = true; }, 2600);
}

// ---------------------------------------------------------------- saving

async function putShader(path, text) {
  const resp = await fetch(`/api/shader?path=${encodeURIComponent(path)}`, {
    method: "PUT",
    headers: { "X-AutoFX": "1", "Content-Type": "text/plain; charset=utf-8" },
    body: text,
  });
  if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
}

// Writes the code with current parameter values as the new defaults, then
// shows that text in the editor so the file and the editor agree.
function adoptSavedText(text) {
  const { selectionStart, selectionEnd, scrollTop } = el.code;
  el.code.value = text;
  el.code.setSelectionRange(selectionStart, selectionEnd);
  el.code.scrollTop = scrollTop;
  state.saved = text;
  state.values = {};
  recompile();
  storeDoc();
}

async function save() {
  if (el.saveBtn.disabled || el.saveBtn.hidden) return;
  const text = textToSave();
  try {
    await putShader(state.path, text);
    adoptSavedText(text);
    renderList();
    toast(`Saved ${state.path}`);
  } catch (e) {
    toast(`Save failed: ${e.message}`);
  }
}

function suggestSaveAsName() {
  const base = state.path.startsWith("local:") ? state.name : state.path;
  return base.replace(/(\.glsl)?$/, "").replace(/-tweaked(-\d+)?$/, "") + "-tweaked.glsl";
}

async function saveAs(path) {
  const text = textToSave();
  try {
    await putShader(path, text);
    storeDoc();
    if (!state.shaders.includes(path)) state.shaders = [...state.shaders, path].sort();
    state.docs.set(path, { saved: text, code: text, values: {}, name: path, writable: true });
    state.path = null;
    openDoc(path, text, { name: path, writable: true });
    toast(`Saved ${path}`);
    return true;
  } catch (e) {
    toast(`Save failed: ${e.message}`);
    return false;
  }
}

function download() {
  const blob = new Blob([textToSave()], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = state.name.split("/").pop() || "shader.glsl";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function copy() {
  try {
    await navigator.clipboard.writeText(textToSave());
    toast("Copied shader with current values as defaults");
  } catch {
    el.code.focus();
    el.code.select();
    toast("Copy blocked; the code is selected instead");
  }
}

// ---------------------------------------------------------------- events

el.code.addEventListener("input", () => {
  renderGutter();
  clearTimeout(compileTimer);
  compileTimer = setTimeout(() => {
    const before = state.settings;
    state.settings = { ...renderSettings(el.code.value), duration: before.duration };
    recompile();
    storeDoc();
    renderList();
  }, 250);
  updateChrome();
});
el.code.addEventListener("scroll", () => { el.gutter.scrollTop = el.code.scrollTop; });
el.code.addEventListener("keydown", (e) => {
  if (e.key === "Tab" && !e.shiftKey) {
    e.preventDefault();
    el.code.setRangeText("    ", el.code.selectionStart, el.code.selectionEnd, "end");
    el.code.dispatchEvent(new Event("input"));
  }
});

el.play.addEventListener("click", () => setPlaying(!state.playing));
el.prev.addEventListener("click", () => stepFrame(-1));
el.next.addEventListener("click", () => stepFrame(1));
el.scrub.addEventListener("input", () => { setPlaying(false); state.t = Number(el.scrub.value); });
el.duration.addEventListener("change", () => {
  const d = Number(el.duration.value);
  if (d > 0) state.settings = { ...state.settings, duration: d };
  el.duration.value = String(state.settings.duration);
});
el.rate.addEventListener("change", () => { state.rate = Number(el.rate.value); });
el.seed.addEventListener("input", () => { state.seed = Number(el.seed.value) || 0; });
el.bg.addEventListener("change", () => {
  el.stage.className = `stage ${el.bg.value}`;
  try { localStorage.setItem("autofx-editor-bg", el.bg.value); } catch {}
});
el.res.addEventListener("change", applyResolution);
el.filter.addEventListener("input", renderList);

el.randomize.addEventListener("click", () => {
  for (const p of state.params) {
    const v = randomValue(p);
    if (sameValue(v, p.default)) delete state.values[p.name];
    else state.values[p.name] = v;
  }
  renderParams();
  updateChrome();
});
el.resetAll.addEventListener("click", () => {
  state.values = {};
  renderParams();
  updateChrome();
});

el.openBtn.addEventListener("click", () => el.openFile.click());
el.openFile.addEventListener("change", () => {
  if (el.openFile.files[0]) openLocalFile(el.openFile.files[0]);
  el.openFile.value = "";
});
el.copyBtn.addEventListener("click", copy);
el.downloadBtn.addEventListener("click", download);
el.saveBtn.addEventListener("click", save);
el.saveAsBtn.addEventListener("click", () => {
  el.saveAsForm.hidden = false;
  el.saveAsName.value = suggestSaveAsName();
  el.saveAsName.focus();
  el.saveAsName.setSelectionRange(0, el.saveAsName.value.length - ".glsl".length);
});
el.saveAsCancel.addEventListener("click", () => { el.saveAsForm.hidden = true; });
el.saveAsForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  let name = el.saveAsName.value.trim();
  if (!name) return;
  if (!name.endsWith(".glsl")) name += ".glsl";
  if (await saveAs(name)) el.saveAsForm.hidden = true;
});

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
    e.preventDefault();
    save();
    return;
  }
  const typing = e.target.closest("input, textarea, select");
  if (typing) return;
  if (e.key === " ") { e.preventDefault(); setPlaying(!state.playing); }
  else if (e.key === "ArrowLeft") stepFrame(-1);
  else if (e.key === "ArrowRight") stepFrame(1);
});

let dragDepth = 0;
window.addEventListener("dragenter", (e) => { e.preventDefault(); dragDepth++; el.drop.hidden = false; });
window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; el.drop.hidden = true; } });
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => {
  e.preventDefault();
  dragDepth = 0;
  el.drop.hidden = true;
  const file = e.dataTransfer?.files?.[0];
  if (file) openLocalFile(file);
});

window.addEventListener("beforeunload", (e) => {
  storeDoc();
  const unsaved = [...state.docs.values()].some((d) => d.writable && setParamDefaults(d.code, d.values) !== d.saved);
  if (unsaved) e.preventDefault();
});

// ---------------------------------------------------------------- startup

async function discover() {
  try {
    const resp = await fetch("/api/shaders", { cache: "no-store" });
    if (resp.ok && resp.headers.get("Content-Type")?.includes("json")) {
      return { source: "server", ...(await resp.json()) };
    }
  } catch {}
  try {
    const resp = await fetch("shaders.json", { cache: "no-store" });
    if (resp.ok) return { source: "static", writable: false, ...(await resp.json()) };
  } catch {}
  return { source: "none", shaders: [], writable: false };
}

async function start() {
  try {
    const bg = localStorage.getItem("autofx-editor-bg");
    if (bg) { el.bg.value = bg; el.stage.className = `stage ${bg}`; }
  } catch {}

  const found = await discover();
  state.source = found.source;
  state.shaders = found.shaders ?? [];
  state.writable = Boolean(found.writable);
  renderList();
  renderParams();
  updateChrome();
  requestAnimationFrame(tick);

  const fromHash = decodeURIComponent(location.hash.slice(1));
  const first = [fromHash, found.initial, state.shaders[0]].find((p) => p && state.shaders.includes(p));
  if (first) await loadShader(first);
}

start();
