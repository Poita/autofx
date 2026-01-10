"""
GIF and sprite sheet creation with transparency support.

Handles the conversion of RGBA frames to:
- Animated GIF format with proper transparency
- PNG sprite sheets for game engines
"""

from typing import List, Optional, Tuple
from pathlib import Path
from PIL import Image
import math
import io


def _prepare_frame_for_gif(frame: Image.Image, threshold: int = 128) -> Image.Image:
    """
    Prepare an RGBA frame for GIF export with transparency.

    GIFs use palette-based transparency (one color = transparent).
    This function converts RGBA to P mode with a consistent transparent color.

    Args:
        frame: RGBA image
        threshold: Alpha threshold below which pixels become transparent

    Returns:
        Palette-mode image ready for GIF export
    """
    if frame.mode != 'RGBA':
        frame = frame.convert('RGBA')

    # Get the alpha channel
    alpha = frame.split()[3]

    # Create a mask of transparent pixels (alpha < threshold)
    mask = Image.eval(alpha, lambda a: 255 if a < threshold else 0)

    # Convert to palette mode with a fixed number of colors
    # Leave room for the transparent color
    p_frame = frame.convert('RGB').convert(
        'P',
        palette=Image.Palette.ADAPTIVE,
        colors=255
    )

    # Set the transparent color index
    # We'll use index 255 for transparent pixels
    p_frame.paste(255, mask)

    return p_frame


def save_gif(
    frames: List[Image.Image],
    output_path: str,
    duration: float,
    loop: int = 0,
    alpha_threshold: int = 128
) -> None:
    """
    Save a list of RGBA frames as an animated GIF with transparency.

    Args:
        frames: List of PIL Images in RGBA mode
        output_path: Path to save the GIF
        duration: Total animation duration in seconds
        loop: Number of times to loop (0 = infinite)
        alpha_threshold: Alpha value below which pixels are considered transparent
    """
    if not frames:
        raise ValueError("No frames to save")

    # Calculate frame duration in milliseconds
    frame_duration_ms = int((duration / len(frames)) * 1000)

    # Minimum GIF frame duration is typically 10ms, but some viewers
    # don't handle very short durations well
    frame_duration_ms = max(frame_duration_ms, 20)

    # Prepare frames for GIF format
    gif_frames = [_prepare_frame_for_gif(f, alpha_threshold) for f in frames]

    # Save the GIF
    gif_frames[0].save(
        output_path,
        save_all=True,
        append_images=gif_frames[1:] if len(gif_frames) > 1 else [],
        duration=frame_duration_ms,
        loop=loop,
        transparency=255,  # Index 255 is transparent
        disposal=2,  # Restore to background between frames
    )


def save_gif_simple(
    frames: List[Image.Image],
    output_path: str,
    duration: float,
    loop: int = 0
) -> None:
    """
    Save frames as GIF without transparency (simpler, more reliable).

    Use this as a fallback if transparency causes issues.

    Args:
        frames: List of PIL Images
        output_path: Path to save the GIF
        duration: Total animation duration in seconds
        loop: Number of times to loop (0 = infinite)
    """
    if not frames:
        raise ValueError("No frames to save")

    frame_duration_ms = int((duration / len(frames)) * 1000)
    frame_duration_ms = max(frame_duration_ms, 20)

    # Convert all frames to RGB (no transparency)
    rgb_frames = [f.convert('RGB') if f.mode != 'RGB' else f for f in frames]

    rgb_frames[0].save(
        output_path,
        save_all=True,
        append_images=rgb_frames[1:] if len(rgb_frames) > 1 else [],
        duration=frame_duration_ms,
        loop=loop,
    )


def frames_to_base64_gif(
    frames: List[Image.Image],
    duration: float,
    with_transparency: bool = True
) -> str:
    """
    Convert frames to a base64-encoded GIF string.

    Useful for embedding in responses or displaying in terminals.

    Args:
        frames: List of PIL Images
        duration: Total animation duration in seconds
        with_transparency: Whether to preserve transparency

    Returns:
        Base64-encoded GIF string
    """
    import base64

    buffer = io.BytesIO()

    if with_transparency:
        frame_duration_ms = int((duration / len(frames)) * 1000)
        frame_duration_ms = max(frame_duration_ms, 20)

        gif_frames = [_prepare_frame_for_gif(f) for f in frames]
        gif_frames[0].save(
            buffer,
            format='GIF',
            save_all=True,
            append_images=gif_frames[1:] if len(gif_frames) > 1 else [],
            duration=frame_duration_ms,
            loop=0,
            transparency=255,
            disposal=2,
        )
    else:
        save_gif_simple_to_buffer(frames, buffer, duration)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def save_gif_simple_to_buffer(
    frames: List[Image.Image],
    buffer: io.BytesIO,
    duration: float
) -> None:
    """Save frames to a BytesIO buffer as GIF."""
    frame_duration_ms = int((duration / len(frames)) * 1000)
    frame_duration_ms = max(frame_duration_ms, 20)

    rgb_frames = [f.convert('RGB') if f.mode != 'RGB' else f for f in frames]

    rgb_frames[0].save(
        buffer,
        format='GIF',
        save_all=True,
        append_images=rgb_frames[1:] if len(rgb_frames) > 1 else [],
        duration=frame_duration_ms,
        loop=0,
    )


def frame_to_base64_png(frame: Image.Image) -> str:
    """
    Convert a single frame to a base64-encoded PNG string.

    Args:
        frame: PIL Image

    Returns:
        Base64-encoded PNG string
    """
    import base64

    buffer = io.BytesIO()

    # Ensure RGBA for transparency support
    if frame.mode != 'RGBA':
        frame = frame.convert('RGBA')

    frame.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def save_spritesheet(
    frames: List[Image.Image],
    output_path: str,
    rows: Optional[int] = None
) -> Tuple[int, int]:
    """
    Save frames as a PNG sprite sheet.

    Frames are arranged in a grid, left-to-right, top-to-bottom.

    Args:
        frames: List of PIL Images in RGBA mode
        output_path: Path to save the PNG sprite sheet
        rows: Number of rows in the grid. If None, auto-calculated for a square-ish layout.

    Returns:
        Tuple of (columns, rows) in the sprite sheet
    """
    if not frames:
        raise ValueError("No frames to save")

    num_frames = len(frames)
    frame_width = frames[0].width
    frame_height = frames[0].height

    # Calculate grid dimensions
    if rows is None:
        # Auto-calculate for approximately square layout
        rows = max(1, int(math.sqrt(num_frames)))
        cols = math.ceil(num_frames / rows)
    else:
        rows = max(1, min(rows, num_frames))
        cols = math.ceil(num_frames / rows)

    # Create the sprite sheet
    sheet_width = cols * frame_width
    sheet_height = rows * frame_height
    spritesheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))

    # Paste frames into the sheet
    for i, frame in enumerate(frames):
        if frame.mode != 'RGBA':
            frame = frame.convert('RGBA')

        col = i % cols
        row = i // cols
        x = col * frame_width
        y = row * frame_height
        spritesheet.paste(frame, (x, y))

    # Save as PNG
    spritesheet.save(output_path, format='PNG')

    return cols, rows


def get_spritesheet_layout(num_frames: int, rows: Optional[int] = None) -> Tuple[int, int]:
    """
    Calculate the sprite sheet grid layout without creating the image.

    Args:
        num_frames: Total number of frames
        rows: Optional number of rows (auto-calculated if None)

    Returns:
        Tuple of (columns, rows)
    """
    if rows is None:
        rows = max(1, int(math.sqrt(num_frames)))
        cols = math.ceil(num_frames / rows)
    else:
        rows = max(1, min(rows, num_frames))
        cols = math.ceil(num_frames / rows)

    return cols, rows
