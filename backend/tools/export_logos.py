# Export medidown logos from SVG to PNG at 1x/2x/4x using CairoSVG
# Run: python e:\\project\\downloader\\tools\\export_logos.py

import os
from pathlib import Path

try:
    import cairosvg
except ImportError:
    raise SystemExit("CairoSVG is required. Install with: venv\\Scripts\\pip.exe install cairosvg")

ROOT = Path(r"e:\\project\\downloader")
STATIC = ROOT / "static"

INPUTS = [
    (STATIC / "logo-medidown-clean.svg", "logo-medidown-clean"),
    (STATIC / "logo-medidown-clean-transparent.svg", "logo-medidown-clean-transparent"),
]

SCALES = [
    (1.0, ""),
    (2.0, "@2x"),
    (4.0, "@4x"),
]

# Dimensions of the SVG canvas
WIDTH = 960
HEIGHT = 260


def export_png(svg_path: Path, base_name: str):
    if not svg_path.exists():
        print(f"Skip: {svg_path} not found")
        return
    with open(svg_path, "rb") as f:
        svg_bytes = f.read()
    for scale, suffix in SCALES:
        out_path = STATIC / f"{base_name}{suffix}.png"
        width_px = int(WIDTH * scale)
        height_px = int(HEIGHT * scale)
        print(f"Exporting {out_path.name} ({width_px}x{height_px})")
        cairosvg.svg2png(bytestring=svg_bytes, write_to=str(out_path), output_width=width_px, output_height=height_px, background_color=None)


def main():
    os.makedirs(STATIC, exist_ok=True)
    for svg_path, base in INPUTS:
        export_png(svg_path, base)
    print("Done.")


if __name__ == "__main__":
    main()