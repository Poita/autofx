# AutoFX

AI-powered visual effects animation generator for games. Describe an effect in plain English and get a transparent GIF animation.

## Examples

| Command | Output |
|---------|--------|
| `autofx "fiery explosion" -f 30 -o explosion.gif` | <img src="examples/explosion.gif" width="128"> |
| `autofx "mystical purple flames" --loop -d 1.5 -f 45 -o magic-flames.gif` | <img src="examples/magic-flames.gif" width="128"> |
| `autofx "glowing energy ball" --loop -f 30 -o energy-ball.gif` | <img src="examples/energy-ball.gif" width="128"> |
| `autofx "healing aura with rising particles" --loop -f 60 -o heal.gif` | <img src="examples/heal.gif" width="128"> |

## How It Works

1. You describe a visual effect (e.g., "fiery explosion")
2. Claude generates a Shadertoy-style GLSL shader
3. The shader is rendered frame-by-frame using ModernGL
4. Output is saved as a transparent GIF (perfect for game sprites)

The Claude agent has access to tools that let it compile, test, and preview shaders before producing the final animation.

## Installation

### macOS

```bash
git clone https://github.com/Poita/autofx.git
cd autofx
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...
```

ModernGL ships prebuilt wheels for macOS, so no system packages needed beyond a working OpenGL (already present on every Mac).

### Linux (headless servers, Docker, etc.)

ModernGL doesn't have prebuilt aarch64 wheels and its `glcontext` extension compiles against several display backends, so a Linux install needs both the build toolchain and runtime + dev libraries for X11/EGL/GL/GLES, even if you're rendering headless.

On Debian / Ubuntu (and its derivatives):

```bash
# Build deps for moderngl's C++ extension
sudo apt install -y g++ python3-dev libx11-dev libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev

# Runtime libs (libosmesa / Mesa software rendering for headless boxes)
sudo apt install -y libegl1 libegl-mesa0 libgl1 libglx-mesa0 libgles2

# Then install autofx
git clone https://github.com/Poita/autofx.git
cd autofx
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...

# Headless rendering hints (no display, no GPU)
export LIBGL_ALWAYS_SOFTWARE=1
export EGL_PLATFORM=surfaceless
```

### Linux (desktop, with a real GPU + display)

Same as the headless instructions but without the `LIBGL_ALWAYS_SOFTWARE` / `EGL_PLATFORM` overrides — your driver handles it.

### Anthropic API key

`autofx` uses the Claude API to generate shaders, so you need an `ANTHROPIC_API_KEY`. Get one from <https://console.anthropic.com/>. Set it before running:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## CLI Usage

```bash
# Basic usage (one-shot effect that dissipates by end)
autofx "fiery explosion" -o explosion.gif

# Looping effect (seamless loop)
autofx "magical flames" --loop -d 2.0 -o flames.gif

# With custom settings
autofx "magic sparkles" --duration 2.0 --resolution 128x128 --frames 20 -o sparkles.gif

# High-quality with more frames
autofx "lightning bolt" -d 1.0 -r 256x256 -f 60 -o lightning.gif

# With PNG sprite sheet (auto grid layout)
autofx "energy ball" -f 16 -s -o energy.gif

# Sprite sheet with specific row count
autofx "coin spin" --loop -f 8 -s --rows 1 -o coin.gif

# Multiple variations with different seeds
autofx "particle burst" -n 3 -o burst.gif
# Output: burst-0.gif, burst-1.gif, burst-2.gif, burst.glsl

# Re-render existing shader at different settings
autofx explosion.glsl -r 512x512 -f 60 -o explosion_hd.gif

# Generate sprite sheet from existing shader
autofx explosion.glsl -s -f 16 -o explosion.gif

# Edit an existing shader with AI
autofx --edit magic-flames.glsl "make the flames blue instead" --loop -d 1.5 -f 45 -o blue-flames.gif

# Tweak shader parameters live in the browser editor
autofx editor examples/
```

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `prompt` | | (required) | Effect description, or `.glsl` file to render |
| `--duration` | `-d` | 1.0 | Animation duration in seconds |
| `--resolution` | `-r` | 256x256 | Output resolution (WxH) |
| `--frames` | `-f` | 10 | Number of frames |
| `--output` | `-o` | output.gif | Output file path |
| `--loop` | `-l` | false | Seamlessly looping effect |
| `--spritesheet` | `-s` | false | Also output a PNG sprite sheet |
| `--rows` | | auto | Rows in sprite sheet |
| `--variations` | `-n` | 1 | Generate N variations with different seeds |
| `--model` | `-m` | opus | Model to use for generation |
| `--edit` | `-e` | | Edit existing `.glsl` file (prompt becomes modification) |
| `--verbose` | `-v` | false | Print detailed progress |

### Variations Example

Generate multiple unique variations from the same prompt using `-n`:

```bash
autofx "colorful particle explosion with sparks flying in random directions" -n 3 -f 30 -o particle-burst.gif
```

| Variation 0 | Variation 1 | Variation 2 |
|-------------|-------------|-------------|
| <img src="examples/particle-burst-0.gif" width="128"> | <img src="examples/particle-burst-1.gif" width="128"> | <img src="examples/particle-burst-2.gif" width="128"> |

Each variation uses a different random seed while sharing the same shader code.

### Edit Example

Modify an existing shader with `--edit`:

```bash
autofx --edit examples/magic-flames.glsl "make the flames blue instead of purple" --loop -d 1.5 -f 45 -o blue-flames.gif
```

| Original | Edited |
|----------|--------|
| <img src="examples/magic-flames.gif" width="128"> | <img src="examples/blue-flames-black.gif" width="128"> |

The AI modifies the shader's color palette while preserving the flame animation structure.

## Shader Editor

`autofx editor` opens a browser editor for tweaking shaders live:

```bash
autofx editor                      # browse every .glsl under the current directory
autofx editor examples/            # browse a folder
autofx editor fire.glsl            # open one shader
autofx editor examples/ --port 9000 --no-browser
```

<img src="examples/editor.jpg" width="720" alt="The AutoFX editor showing an explosion shader with its parameter sliders">

- **Live preview** rendered with WebGL2, with play/pause, a time scrubber, frame stepping, playback speed, seed, background (checker, black, gray, white) and preview resolution.
- **Parameter controls** generated from the shader's `// @param` lines (see [Tweakable Parameters](#tweakable-parameters)): sliders for numbers and vectors, color pickers, toggles, per-parameter reset, Reset all and Randomize.
- **Code editing** with live recompiling. Errors appear under the code with line numbers that match your file.
- **Save** (⌘S / Ctrl+S) writes the code to disk with the current parameter values as the new defaults, so `autofx fire.glsl -o fire.gif` renders exactly what you see. **Save as…** writes a copy instead. Copy and Download give you the same text.

Keys: Space plays and pauses; ← and → step one output frame. Unsaved edits are kept per shader while you switch between them.

The server only listens on `127.0.0.1` and only reads and writes `.glsl` files under the folder it was started on.

## Library Usage

### High-Level API (with Claude Agent)

```python
import asyncio
from autofx import generate_vfx

async def main():
    result = await generate_vfx(
        prompt="fiery explosion",
        duration=1.0,
        resolution=(256, 256),
        frames=10,
        output_path="explosion.gif"
    )

    if result["success"]:
        print(f"GIF saved to: {result['gif_path']}")
        print(f"Shader saved to: {result['shader_path']}")
    else:
        print(f"Failed: {result['error']}")

asyncio.run(main())
```

### Low-Level API (Direct Shader Rendering)

If you already have shader code, you can render it directly:

```python
from autofx import render_shader, save_gif

shader_code = '''
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec2 center = vec2(0.5);
    float dist = length(uv - center);

    // Animated circle
    float radius = 0.3 + 0.1 * sin(iTime * 3.0);
    float circle = smoothstep(radius + 0.02, radius - 0.02, dist);

    // Color
    vec3 color = vec3(1.0, 0.5, 0.0) * circle;

    fragColor = vec4(color, circle);
}
'''

# Render frames
frames = render_shader(
    shader_code=shader_code,
    duration=1.0,
    resolution=(256, 256),
    num_frames=10
)

# Override @param values (unlisted parameters use their defaults)
hot = render_shader(shader_code, 1.0, (256, 256), 10, params={"intensity": 1.8, "coreColor": "#a0e0ff"})

# Save as GIF
save_gif(frames, "circle.gif", duration=1.0)
```

### Using ShaderRenderer Directly

For more control over the rendering process:

```python
from autofx import ShaderRenderer

with ShaderRenderer(256, 256) as renderer:
    # Compile once
    success, error = renderer.compile_shader(shader_code)
    if not success:
        print(f"Compile error: {error}")
    else:
        # Render individual frames
        frame_0 = renderer.render(shader_code, time=0.0)
        frame_1 = renderer.render(shader_code, time=0.5)
        frame_2 = renderer.render(shader_code, time=1.0)

        # Save frames as PNG
        frame_0.save("frame_0.png")
        frame_1.save("frame_1.png")
        frame_2.save("frame_2.png")
```

## Shader Format

AutoFX uses Shadertoy-style GLSL shaders:

```glsl
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // fragCoord: pixel coordinates (0 to iResolution.xy)
    // fragColor: output color (RGBA)

    vec2 uv = fragCoord / iResolution.xy;  // Normalize to 0-1

    // Use iTime for animation (0 to duration)
    float t = iTime;

    // Set output color with alpha for transparency
    fragColor = vec4(color, alpha);
}
```

### Available Uniforms

| Uniform | Type | Description |
|---------|------|-------------|
| `iTime` | float | Current time in seconds (0 to duration) |
| `iResolution` | vec3 | Viewport resolution (width, height, 1.0) |
| `iSeed` | float | Random seed for variations (use with `-n`) |

### Tweakable Parameters

Shaders declare the knobs worth tweaking as comment lines, one per parameter:

```glsl
// @param <name> <type> <default> [min, max] "description"
```

```glsl
// @param flameSpeed int 2 [1, 4] "Flicker cycles per loop"
// @param flameHeight float 0.55 [0.3, 0.75] "Flame height as a fraction of the frame"
// @param coreColor color #fff1c2 "Color of the hottest part of the flame"
// @param wind vec2 (0.1, 0.0) [-1, 1] "Wind pushing the flame"
// @param showSmoke bool true "Draw a faint smoke trail"

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // flameSpeed, flameHeight, coreColor, ... are ready to use here
}
```

| Type | Default | Range | In GLSL |
|------|---------|-------|---------|
| `float` | `1.5` | required | `float` |
| `int` | `24` | required, whole numbers | `int` |
| `bool` | `true` / `false` | none | `bool` |
| `color` | `#ffb547` | none | `vec3` (RGB, 0-1) |
| `vec2` | `(0.2, -0.5)` | required, per component | `vec2` |
| `vec3` | `(1.0, 0.5, 0.25)` | required, per component | `vec3` |

Each line declares its uniform, so the shader uses the name without declaring it. The default must sit inside the range, and the description is optional. Renders use the defaults unless you pass overrides (`render_shader(..., params={...})`), and the [editor](#shader-editor) builds its controls from these lines.

Generated shaders come with 4-10 parameters picked for the effect (speed, size, intensity, colors, counts, turbulence, ...). Their ranges are chosen so every value keeps the effect in frame, keeps loops seamless and still lets one-shots finish. Shaders are also written to compile as GLSL ES 3.00, so they run in the browser editor.

### Transparency

Use the alpha channel for transparency:

```glsl
// Fully opaque pixel
fragColor = vec4(1.0, 0.0, 0.0, 1.0);

// Fully transparent pixel
fragColor = vec4(0.0, 0.0, 0.0, 0.0);

// Semi-transparent
fragColor = vec4(color, 0.5);
```

## Output Files

When you run `autofx "effect" -o effect.gif`, you get:

- `effect.gif` - Animated GIF with transparent background
- `effect.glsl` - Shader source code (includes re-render command in comments)

With `-s/--spritesheet`: also `effect.png` sprite sheet.

With `-n 3`: produces `effect-0.gif`, `effect-1.gif`, `effect-2.gif` + one `effect.glsl`.

The `.glsl` file can be re-rendered at any time: `autofx effect.glsl -r 512x512 -o effect_hd.gif`

## Requirements

- Python 3.10+
- OpenGL 3.3+ compatible graphics driver
- Anthropic API key (for Claude Agent)

## Troubleshooting

### "moderngl.Error: cannot create context"

You're missing OpenGL/EGL libraries or the headless rendering environment isn't configured. See the [Linux installation section](#linux-headless-servers-docker-etc) — install the apt packages and export `LIBGL_ALWAYS_SOFTWARE=1` and `EGL_PLATFORM=surfaceless`.

### Compile error: `glcontext/x11.cpp:5:10: fatal error: X11/Xlib.h: No such file or directory`

`moderngl`'s context module is being compiled from source and it needs X11 dev headers even in a headless build (it tries every display backend at compile time):

```bash
sudo apt install -y libx11-dev libgl1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev
```

### Compile error: `aarch64-linux-gnu-g++: No such file or directory`

You're on ARM64 Linux without a C++ toolchain. ModernGL doesn't ship aarch64 wheels yet, so it compiles from source:

```bash
sudo apt install -y g++ python3-dev
```

### "claude-agent-sdk not found"

Install the Claude Agent SDK:

```bash
pip install claude-agent-sdk
```

### "Agent did not produce output files" / "does not support this model"

Your `claude-agent-sdk` bundles a Claude Code CLI that is too old for the default model. Upgrade it:

```bash
pip install -U "claude-agent-sdk>=0.2.158"
```

### "ANTHROPIC_API_KEY not set"

Set your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Gallery

A showcase of effects generated with AutoFX:

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="examples/gallery/explosion.gif" width="128"><br>Explosion | <img src="examples/gallery/sparkles.gif" width="128"><br>Sparkles | <img src="examples/gallery/lightning.gif" width="128"><br>Lightning | <img src="examples/gallery/energy-orb.gif" width="128"><br>Energy Orb |
| <img src="examples/gallery/smoke.gif" width="128"><br>Smoke | <img src="examples/gallery/ripple.gif" width="128"><br>Ripple | <img src="examples/gallery/torch.gif" width="128"><br>Torch | <img src="examples/gallery/ice.gif" width="128"><br>Ice |
| <img src="examples/gallery/heal.gif" width="128"><br>Heal | <img src="examples/gallery/shock.gif" width="128"><br>Shock | <img src="examples/gallery/portal.gif" width="128"><br>Portal | <img src="examples/gallery/firework.gif" width="128"><br>Firework |
| <img src="examples/gallery/runes.gif" width="128"><br>Runes | <img src="examples/gallery/meteor.gif" width="128"><br>Meteor | <img src="examples/gallery/poison.gif" width="128"><br>Poison | <img src="examples/gallery/shockwave.gif" width="128"><br>Shockwave |

## Development

```bash
pip install -e ".[dev]"
pytest                               # Python tests
node --test tests/js/*.test.mjs      # editor tests (Node 18+)
```

`tests/param_cases.json` holds the `@param` cases both the Python parser (`autofx/params.py`) and the editor's parser (`autofx/editor/params.js`) must agree on.

## License

MIT
