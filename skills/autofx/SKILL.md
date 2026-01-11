---
name: autofx
description: Generate transparent GIF animations of visual effects (explosions, magic, particles, fire) using AI-generated GLSL shaders. Use when creating game sprites, VFX assets, or animated effects.
allowed-tools:
  - Bash
---

# AutoFX - AI Visual Effects Generator

Generate transparent GIF animations of visual effects using AI-generated GLSL shaders. Perfect for game sprites and visual assets.

## CLI Usage

The prompt can be very detailed and specific - more detail produces better results:

```bash
# Basic prompt
autofx "fiery explosion" -o explosion.gif

# Detailed prompt (recommended)
autofx "bright orange and yellow explosion with sparks flying outward, smoke dissipating at the edges, starts intense then fades to embers" -o explosion.gif

# Specific art style
autofx "pixel-art style magic missile, glowing blue projectile with trailing sparkles, 16-bit retro aesthetic" -f 16 -s -o missile.gif

# Looping with details
autofx "ethereal purple flame with swirling wisps, inner white core, outer violet glow pulsing gently" --loop -d 2.0 -o flames.gif

# Specific colors and behavior
autofx "electric cyan lightning bolt striking from top center, bright flash at impact point, crackling energy tendrils spreading outward then fading" -f 60 -o lightning.gif

# Game-specific effects
autofx "healing aura effect, soft green particles rising upward, gentle golden shimmer, peaceful and magical feeling" --loop -f 32 -s -o heal.gif

# Sprite sheet with specific layout
autofx "spinning gold coin with shine glint, metallic reflections" --loop -f 8 -s --rows 1 -o coin.gif

# Multiple variations with different seeds
autofx "particle explosion with random sparks" -n 3 -o explosion.gif
# Produces: explosion-0.gif, explosion-1.gif, explosion-2.gif

# Re-render existing shader (no AI, just render)
autofx explosion.glsl -r 512x512 -f 60 -o explosion_hd.gif
autofx explosion.glsl -s -o explosion.gif  # Generate sprite sheet
```

**Prompt tips:**
- Describe colors explicitly (e.g., "bright orange and cyan" not just "colorful")
- Specify movement/behavior (e.g., "particles rising upward", "expanding outward")
- Include timing (e.g., "starts intense then fades", "pulsing gently")
- Mention art style if relevant (e.g., "pixel-art", "hand-drawn", "realistic")
- Describe the mood/feeling for abstract effects

## Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `prompt` | | required | Effect description, or `.glsl` file to render |
| `--duration` | `-d` | 1.0 | Animation duration in seconds |
| `--resolution` | `-r` | 256x256 | Output resolution (WxH) |
| `--frames` | `-f` | 10 | Number of frames (use 30-60 for smooth animation) |
| `--output` | `-o` | output.gif | Output file path |
| `--loop` | `-l` | false | Seamlessly looping effect |
| `--spritesheet` | `-s` | false | Also output PNG sprite sheet |
| `--rows` | | auto | Rows in sprite sheet |
| `--variations` | `-n` | 1 | Generate N variations with different seeds |
| `--model` | `-m` | opus | Model override (e.g., `claude-sonnet-4-20250514`) |
| `--verbose` | `-v` | false | Show full agent output |

## Output Files

Running `autofx "effect" -o effect.gif` produces:
- `effect.gif` - Animated GIF with transparency
- `effect.glsl` - Shader source (includes re-render command in comments)

With `-s`: also produces `effect.png` sprite sheet.

With `-n 3`: produces `effect-0.gif`, `effect-1.gif`, `effect-2.gif` + one `effect.glsl`.

## Tips

1. **For game sprites**: Use `-s` for sprite sheets, `-f 16` or `-f 32` for frame counts
2. **For looping effects**: Use `--loop` for fire, magic auras, idle animations
3. **For one-shot effects**: Default mode - explosions, impacts, spell casts
4. **Higher quality**: Use more frames (`-f 60`) - rendering is offline
5. **Edit shaders**: The `.glsl` file can be manually edited and re-rendered
6. **Variations**: Use `-n 3` for effects with randomness to get multiple unique outputs
7. **Re-render**: Pass a `.glsl` file to render at different settings without AI

## Python API

```python
from autofx import generate_vfx, render_shader, save_gif

# High-level (uses Claude agent)
result = await generate_vfx(
    prompt="fiery explosion",
    duration=1.0,
    resolution=(256, 256),
    frames=30,
    output_path="explosion.gif",
    loop=False,
    variations=1,          # N variations with different seeds
    model=None             # Override model
)

# Low-level (render existing shader)
frames = render_shader(shader_code, duration=1.0, resolution=(256, 256), num_frames=30, seed=0.0)
save_gif(frames, "output.gif", duration=1.0)
```

## Source Code

Located at `/Users/peter/autofx/`
