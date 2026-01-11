"""
Command-line interface for AutoFX.

Usage:
    autofx "fiery explosion" --duration 1.0 --resolution 256x256 --frames 10 -o explosion.gif
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Tuple


def parse_resolution(value: str) -> Tuple[int, int]:
    """Parse resolution string like '256x256' into (width, height) tuple."""
    try:
        parts = value.lower().split('x')
        if len(parts) != 2:
            raise ValueError
        width, height = int(parts[0]), int(parts[1])
        if width <= 0 or height <= 0:
            raise ValueError
        return width, height
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid resolution '{value}'. Use format WIDTHxHEIGHT (e.g., 256x256)"
        )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="autofx",
        description="Generate visual effects animations using AI-powered GLSL shaders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # One-shot effect (dissipates by end)
    autofx "fiery explosion" -o explosion.gif

    # Looping effect (seamless loop)
    autofx "magical flames" --loop -d 2.0 -o flames.gif

    # High-quality with more frames
    autofx "lightning strike" -d 1.0 -r 256x256 -f 60 -o lightning.gif

    # With PNG sprite sheet (auto grid layout)
    autofx "energy ball" -f 16 -s -o energy.gif

    # Sprite sheet with specific row count
    autofx "coin spin" --loop -f 8 -s --rows 1 -o coin.gif

The generated shader code is automatically saved alongside the GIF.
For example, explosion.gif will have explosion.glsl saved next to it.
With -s/--spritesheet, a PNG sprite sheet is also saved (e.g., explosion.png).
        """
    )

    parser.add_argument(
        "prompt",
        type=str,
        help="Description of the visual effect (e.g., 'fiery explosion')"
    )

    parser.add_argument(
        "-d", "--duration",
        type=float,
        default=1.0,
        help="Animation duration in seconds (default: 1.0)"
    )

    parser.add_argument(
        "-r", "--resolution",
        type=parse_resolution,
        default=(256, 256),
        metavar="WxH",
        help="Output resolution as WIDTHxHEIGHT (default: 256x256)"
    )

    parser.add_argument(
        "-f", "--frames",
        type=int,
        default=10,
        help="Number of frames to generate (default: 10)"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output.gif",
        help="Output file path (default: output.gif)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed progress messages"
    )

    parser.add_argument(
        "-l", "--loop",
        action="store_true",
        help="Create a seamlessly looping effect (default: one-shot effect that dissipates)"
    )

    parser.add_argument(
        "-s", "--spritesheet",
        action="store_true",
        help="Also output a PNG sprite sheet (all frames in a grid)"
    )

    parser.add_argument(
        "--rows",
        type=int,
        default=None,
        help="Number of rows in sprite sheet (default: auto-calculated for square-ish layout)"
    )

    return parser


async def run_async(args: argparse.Namespace) -> int:
    """Run the VFX generation asynchronously."""
    from .agent import generate_vfx
    from .gif import save_spritesheet, get_spritesheet_layout
    from .renderer import render_shader

    # Ensure output path has .gif extension
    output_path = args.output
    if not output_path.lower().endswith('.gif'):
        output_path += '.gif'

    print(f"Generating VFX: {args.prompt}")
    print(f"  Resolution: {args.resolution[0]}x{args.resolution[1]}")
    print(f"  Duration: {args.duration}s")
    print(f"  Frames: {args.frames}")
    print(f"  Mode: {'looping' if args.loop else 'one-shot (dissipates)'}")
    print(f"  Output: {output_path}")
    if args.spritesheet:
        cols, rows = get_spritesheet_layout(args.frames, args.rows)
        print(f"  Sprite sheet: {cols}x{rows} grid")
    print()

    try:
        result = await generate_vfx(
            prompt=args.prompt,
            duration=args.duration,
            resolution=args.resolution,
            frames=args.frames,
            output_path=output_path,
            verbose=args.verbose,
            loop=args.loop
        )

        if result["success"]:
            print()
            print("Success!")
            print(f"  GIF: {result['gif_path']}")
            print(f"  Shader: {result['shader_path']}")

            # Generate sprite sheet if requested
            if args.spritesheet and result.get("shader_code"):
                spritesheet_path = Path(output_path).with_suffix('.png')
                print(f"  Generating sprite sheet...")

                # Re-render frames for the sprite sheet
                frames = render_shader(
                    shader_code=result["shader_code"],
                    duration=args.duration,
                    resolution=args.resolution,
                    num_frames=args.frames
                )

                cols, rows = save_spritesheet(frames, str(spritesheet_path), args.rows)
                sheet_width = cols * args.resolution[0]
                sheet_height = rows * args.resolution[1]
                print(f"  Sprite sheet: {spritesheet_path} ({sheet_width}x{sheet_height}, {cols}x{rows} grid)")

            return 0
        else:
            print()
            print(f"Error: {result['error']}")
            return 1

    except ImportError as e:
        print(f"Error: {e}")
        print()
        print("Make sure you have the required dependencies installed:")
        print("  pip install claude-agent-sdk moderngl pillow numpy")
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate arguments
    if args.duration <= 0:
        print("Error: Duration must be positive")
        return 1

    if args.frames <= 0:
        print("Error: Frames must be positive")
        return 1

    if args.frames < 2:
        print("Warning: Using only 1 frame won't produce an animation")

    # Run the async generation
    return asyncio.run(run_async(args))


if __name__ == "__main__":
    sys.exit(main())
