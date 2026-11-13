"""Deterline — Pixel Background Generator (P4-2)

Pure Python/PIL background generation for users without image editing software.
All functions generate simple pixel art backgrounds and save to PNG.

Usage:
    python bg_generator.py --pattern gradient \\
        --colors "#1a1a2e,#16213e,#0f3460" \\
        --width 640 --height 480 --output bg.png
"""

__version__ = "2.5.2"

import argparse
import math
import random
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None
    _PIL_AVAILABLE = False
else:
    _PIL_AVAILABLE = True


def _require_pil():
    if not _PIL_AVAILABLE:
        raise ImportError("PIL (Pillow) is required. Install: pip install Pillow")


def _parse_colors(colors: list[str]) -> list[tuple[int, int, int]]:
    """Parse hex color strings into (R,G,B) tuples."""
    result = []
    for c in colors:
        c = c.lstrip("#")
        if len(c) == 3:
            c = "".join(x * 2 for x in c)
        if len(c) != 6:
            raise ValueError(f"Invalid color: #{c}")
        r = int(c[0:2], 16)
        g = int(c[2:4], 16)
        b = int(c[4:6], 16)
        result.append((r, g, b))
    return result


def generate_gradient(path: str | Path, width: int, height: int,
                      colors: list[str], direction: str = "vertical") -> str:
    """Generate a vertical or horizontal gradient.
    
    Args:
        colors: List of 2-10 hex color strings (e.g. ["#1a1a2e", "#0f3460"])
        direction: "vertical" or "horizontal"
    """
    _require_pil()
    colors_rgb = _parse_colors(colors)
    img = Image.new("RGB", (width, height))
    
    n = len(colors_rgb) - 1
    if n == 0:
        img.paste(colors_rgb[0], (0, 0, width, height))
    else:
        for i in range(width * height):
            x = i % width
            y = i // width
            if direction == "vertical":
                t = y / max(height - 1, 1)
            else:
                t = x / max(width - 1, 1)
            t = max(0.0, min(1.0, t))
            seg = t * n
            idx = int(seg)
            frac = seg - idx
            if idx >= n:
                idx = n - 1
                frac = 1.0
            c1 = colors_rgb[idx]
            c2 = colors_rgb[idx + 1]
            r = int(c1[0] + (c2[0] - c1[0]) * frac)
            g = int(c1[1] + (c2[1] - c1[1]) * frac)
            b = int(c1[2] + (c2[2] - c1[2]) * frac)
            img.putpixel((x, y), (r, g, b))
    
    out = Path(path)
    img.save(str(out))
    return str(out)


def generate_stripes(path: str | Path, width: int, height: int,
                     colors: list[str], stripe_width: int = 32,
                     angle: int = 0) -> str:
    """Generate striped pattern.
    
    Args:
        colors: List of 2-10 hex colors
        stripe_width: Width of each stripe in pixels
        angle: 0=horizontal, 90=vertical (only these two supported)
    """
    _require_pil()
    colors_rgb = _parse_colors(colors)
    img = Image.new("RGB", (width, height))
    
    for y in range(height):
        for x in range(width):
            if angle == 90:
                idx = (x // stripe_width) % len(colors_rgb)
            else:
                idx = (y // stripe_width) % len(colors_rgb)
            img.putpixel((x, y), colors_rgb[idx])
    
    out = Path(path)
    img.save(str(out))
    return str(out)


def generate_checkerboard(path: str | Path, width: int, height: int,
                          colors: list[str], tile_size: int = 64) -> str:
    """Generate checkerboard pattern.
    
    Args:
        colors: Exactly 2 hex colors (e.g. ["#2d2d2d", "#404040"])
        tile_size: Size of each checkerboard tile in pixels
    """
    _require_pil()
    colors_rgb = _parse_colors(colors)
    if len(colors_rgb) < 2:
        colors_rgb = colors_rgb * 2
    img = Image.new("RGB", (width, height))
    
    for y in range(height):
        for x in range(width):
            tx = x // tile_size
            ty = y // tile_size
            idx = (tx + ty) % 2
            img.putpixel((x, y), colors_rgb[idx])
    
    out = Path(path)
    img.save(str(out))
    return str(out)


def generate_dotted(path: str | Path, width: int, height: int,
                    bg_color: str = "#1a1a2e",
                    dot_color: str = "#3498db",
                    dot_radius: int = 4, spacing: int = 32) -> str:
    """Generate dotted pattern (e.g. starfield-like).
    
    Args:
        bg_color: Background hex color
        dot_color: Dot hex color
        dot_radius: Dot radius in pixels
        spacing: Grid spacing between dots in pixels
    """
    _require_pil()
    bg = _parse_colors([bg_color])[0]
    dot = _parse_colors([dot_color])[0]
    img = Image.new("RGB", (width, height), bg)
    
    for y in range(0, height, spacing):
        for x in range(0, width, spacing):
            for dy in range(-dot_radius, dot_radius + 1):
                for dx in range(-dot_radius, dot_radius + 1):
                    if dx * dx + dy * dy <= dot_radius * dot_radius:
                        px = x + dx
                        py = y + dy
                        if 0 <= px < width and 0 <= py < height:
                            img.putpixel((px, py), dot)
    
    out = Path(path)
    img.save(str(out))
    return str(out)


def generate_starfield(path: str | Path, width: int, height: int,
                       star_count: int = 200,
                       bg_color: str = "#000000",
                       star_color: str = "#ffffff",
                       twinkle: bool = False) -> str:
    """Generate a random starfield background.
    
    Args:
        star_count: Number of stars
        bg_color: Background hex color
        star_color: Star hex color
        twinkle: If True, vary star brightness randomly
    """
    _require_pil()
    bg = _parse_colors([bg_color])[0]
    star = _parse_colors([star_color])[0]
    img = Image.new("RGB", (width, height), bg)
    
    for _ in range(star_count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        if twinkle:
            brightness = random.uniform(0.3, 1.0)
            c = (int(star[0] * brightness), int(star[1] * brightness), int(star[2] * brightness))
        else:
            c = star
        size = random.choices([1, 2, 3], weights=[10, 3, 1])[0]
        for dy in range(-size, size + 1):
            for dx in range(-size, size + 1):
                if dx * dx + dy * dy <= size * size:
                    px = x + dx
                    py = y + dy
                    if 0 <= px < width and 0 <= py < height:
                        img.putpixel((px, py), c)
    
    out = Path(path)
    img.save(str(out))
    return str(out)


PATTERNS = {
    "gradient": generate_gradient,
    "stripes": generate_stripes,
    "checkerboard": generate_checkerboard,
    "dotted": generate_dotted,
    "starfield": generate_starfield,
}


def main():
    parser = argparse.ArgumentParser(description="Deterline — Pixel Background Generator")
    parser.add_argument("--pattern", choices=list(PATTERNS.keys()), default="gradient")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--colors", type=str, default="#1a1a2e,#0f3460",
                        help="Comma-separated hex colors")
    parser.add_argument("--bg-color", type=str, default="#000000",
                        help="Background hex color (dotted, starfield)")
    parser.add_argument("--dot-color", type=str, default="#3498db",
                        help="Dot hex color (dotted)")
    parser.add_argument("--dot-radius", type=int, default=4,
                        help="Dot radius (dotted)")
    parser.add_argument("--spacing", type=int, default=32,
                        help="Grid spacing (dotted)")
    parser.add_argument("--stripe-width", type=int, default=32,
                        help="Stripe width (stripes)")
    parser.add_argument("--angle", type=int, default=0, choices=[0, 90],
                        help="Stripe angle (stripes)")
    parser.add_argument("--tile-size", type=int, default=64,
                        help="Tile size (checkerboard)")
    parser.add_argument("--star-count", type=int, default=200,
                        help="Star count (starfield)")
    parser.add_argument("--star-color", type=str, default="#ffffff",
                        help="Star hex color (starfield)")
    parser.add_argument("--twinkle", action="store_true",
                        help="Vary star brightness (starfield)")
    parser.add_argument("--output", type=str, default="bg_output.png",
                        help="Output PNG path")
    args = parser.parse_args()
    
    colors = [c.strip() for c in args.colors.split(",")]
    
    fn = PATTERNS[args.pattern]
    kwargs = {
        "path": args.output,
        "width": args.width,
        "height": args.height,
    }
    
    if args.pattern == "gradient":
        kwargs["colors"] = colors
    elif args.pattern == "stripes":
        kwargs["colors"] = colors
        kwargs["stripe_width"] = args.stripe_width
        kwargs["angle"] = args.angle
    elif args.pattern == "checkerboard":
        kwargs["colors"] = colors
        kwargs["tile_size"] = args.tile_size
    elif args.pattern == "dotted":
        kwargs["bg_color"] = args.bg_color
        kwargs["dot_color"] = args.dot_color
        kwargs["dot_radius"] = args.dot_radius
        kwargs["spacing"] = args.spacing
    elif args.pattern == "starfield":
        kwargs["star_count"] = args.star_count
        kwargs["bg_color"] = args.bg_color
        kwargs["star_color"] = colors[0] if colors else "#ffffff"
        kwargs["twinkle"] = args.twinkle
    
    result = fn(**kwargs)
    print(f"OK: Generated {result} ({args.width}x{args.height})")


if __name__ == "__main__":
    main()
