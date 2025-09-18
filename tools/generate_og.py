from PIL import Image, ImageDraw, ImageFont
import os

# Output path (frontend root)
OUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'og-default.png'))
WIDTH, HEIGHT = 1200, 630

# Brand colors
START_HEX = "#0EA5E9"  # sky blue
END_HEX   = "#9333EA"  # purple

# Create diagonal gradient background (top-left -> bottom-right)
img = Image.new('RGB', (WIDTH, HEIGHT), START_HEX)
draw = ImageDraw.Draw(img)

# Convert hex to rgb
hex_to_rgb = lambda h: tuple(int(h[i:i+2], 16) for i in (1,3,5))
rs, gs, bs = hex_to_rgb(START_HEX)
re, ge, be = hex_to_rgb(END_HEX)

# Diagonal interpolation factor along x+y
max_d = (WIDTH - 1) + (HEIGHT - 1)
for y in range(HEIGHT):
    for x in range(WIDTH):
        t = (x + y) / max_d
        r = int(rs * (1 - t) + re * t)
        g = int(gs * (1 - t) + ge * t)
        b = int(bs * (1 - t) + be * t)
        draw.point((x, y), fill=(r, g, b))

# Add title text
title = "ClipJet"
subtitle = "Free Online Video Downloader"

# Try to load a decent font; fallback to default
font_paths = [
    "C:/Windows/Fonts/SegoeUI.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

def choose_font(size):
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

font_title = choose_font(96)
font_sub = choose_font(36)

# Text sizes using textbbox
bbox_title = draw.textbbox((0,0), title, font=font_title)
w_title, h_title = bbox_title[2]-bbox_title[0], bbox_title[3]-bbox_title[1]
bbox_sub = draw.textbbox((0,0), subtitle, font=font_sub)
w_sub, h_sub = bbox_sub[2]-bbox_sub[0], bbox_sub[3]-bbox_sub[1]

cx, cy = WIDTH // 2, HEIGHT // 2

# Draw shadow for better contrast
shadow_offset = 3
for dx, dy in [(shadow_offset, shadow_offset)]:
    draw.text((cx - w_title//2 + dx, cy - h_title - 10 + dy), title, font=font_title, fill=(0,0,0,90))
    draw.text((cx - w_sub//2 + dx, cy + 10 + dy), subtitle, font=font_sub, fill=(0,0,0,90))

# Draw main text
draw.text((cx - w_title//2, cy - h_title - 10), title, font=font_title, fill=(255,255,255))
draw.text((cx - w_sub//2, cy + 10), subtitle, font=font_sub, fill=(234,248,255))

# Save
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
img.save(OUT_PATH, format='PNG')
print("Wrote:", OUT_PATH)