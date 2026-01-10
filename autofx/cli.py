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
    autofx "fiery explosion" -o explosion.gif
    autofx "magic sparkles" --duration 2.0 --resolution 128x128 --frames 20 -o sparkles.gif
    autofx "swirling vortex" -d 1.5 -r 256x256 -f 15 -o vortex.gif

The generated shader code is automatically saved alongside the GIF.
For example, explosion.gif will have explosion.glsl saved next to it.
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
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts if generation fails (default: 3)"
    )

    return parser


async def run_async(args: argparse.Namespace) -> int:
    """Run the VFX generation asynchronously."""
    from .agent import generate_vfx

    # Ensure output path has .gif extension
    output_path = args.output
    if not output_path.lower().endswith('.gif'):
        output_path += '.gif'

    print(f"Generating VFX: {args.prompt}")
    print(f"  Resolution: {args.resolution[0]}x{args.resolution[1]}")
    print(f"  Duration: {args.duration}s")
    print(f"  Frames: {args.frames}")
    print(f"  Output: {output_path}")
    print()

    try:
        result = await generate_vfx(
            prompt=args.prompt,
            duration=args.duration,
            resolution=args.resolution,
            frames=args.frames,
            output_path=output_path,
            max_retries=args.max_retries,
            verbose=args.verbose
        )

        if result["success"]:
            print()
            print("Success!")
            print(f"  GIF: {result['gif_path']}")
            print(f"  Shader: {result['shader_path']}")
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
