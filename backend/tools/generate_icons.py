from PIL import Image, ImageDraw, ImageFont
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'frontend')

# Brand gradient colors
START_HEX = '#0EA5E9'  # blue (top-left)
END_HEX   = '#9333EA'  # purple (bottom-right)

# Utilities
hex_to_rgb = lambda h: tuple(int(h[i:i+2], 16) for i in (1,3,5))


def make_gradient(size):
    w = h = size
    img = Image.new('RGBA', (w, h), START_HEX)
    draw = ImageDraw.Draw(img)
    rs, gs, bs = hex_to_rgb(START_HEX)
    re, ge, be = hex_to_rgb(END_HEX)
    max_d = (w - 1) + (h - 1)
    for y in range(h):
        for x in range(w):
            t = (x + y) / max_d
            r = int(rs * (1 - t) + re * t)
            g = int(gs * (1 - t) + ge * t)
            b = int(bs * (1 - t) + be * t)
            draw.point((x, y), fill=(r, g, b, 255))
    return img


def choose_font(size):
    font_paths = [
        'C:/Windows/Fonts/SegoeUI.ttf',
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/ARIAL.TTF',
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_mark(base_img):
    img = base_img.copy()
    w, h = img.size
    draw = ImageDraw.Draw(img)

    # Optional: rounded square backdrop for better contrast
    radius = int(min(w, h) * 0.18)
    pad = int(min(w, h) * 0.10)
    rect = [pad, pad, w - pad, h - pad]
    draw.rounded_rectangle(rect, radius=radius, fill=(255, 255, 255, 28), outline=None)

    # Letter mark "C"
    font_size = int(min(w, h) * 0.55)
    font = choose_font(font_size)
    text = 'C'
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx, cy = w // 2, h // 2
    # subtle shadow
    draw.text((cx - tw // 2 + 2, cy - th // 2 + 3), text, font=font, fill=(0, 0, 0, 90))
    # main glyph
    draw.text((cx - tw // 2, cy - th // 2), text, font=font, fill=(255, 255, 255, 255))
    return img


def generate_all():
    os.makedirs(OUT, exist_ok=True)

    # Base large artwork
    base512 = draw_mark(make_gradient(512))

    # PNG icons
    out_512 = os.path.join(OUT, 'icon-512.png')
    out_192 = os.path.join(OUT, 'icon-192.png')
    out_apple = os.path.join(OUT, 'apple-touch-icon.png')  # 180x180

    base512.save(out_512, format='PNG')
    base512.resize((192, 192), Image.LANCZOS).save(out_192, format='PNG')
    base512.resize((180, 180), Image.LANCZOS).save(out_apple, format='PNG')

    # Favicon ICO with multiple sizes
    favicon_path = os.path.join(OUT, 'favicon.ico')
    base512.save(favicon_path, sizes=[(16,16), (32,32), (48,48)])

    print('Wrote:', out_512)
    print('Wrote:', out_192)
    print('Wrote:', out_apple)
    print('Wrote:', favicon_path)


if __name__ == '__main__':
    generate_all()