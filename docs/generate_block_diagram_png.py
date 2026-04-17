from PIL import Image, ImageDraw, ImageFont
import math

W, H = 1400, 500
img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)


def f(size, bold=False):
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def box(x1, y1, x2, y2, text, fill, stroke):
    draw.rounded_rectangle((x1, y1, x2, y2), radius=18, fill=fill, outline=stroke, width=4)
    ft = f(22, True)
    l, t, r, b = draw.textbbox((0, 0), text, font=ft)
    draw.text((x1 + (x2 - x1 - (r - l)) // 2, y1 + (y2 - y1 - (b - t)) // 2), text, fill="#111827", font=ft)


def arrow(x1, y1, x2, y2):
    draw.line((x1, y1, x2, y2), fill="#4b5563", width=5)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 12
    p1 = (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45))
    p2 = (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45))
    draw.polygon([(x2, y2), p1, p2], fill="#4b5563")


draw.text((470, 30), "Simple Block Diagram (High-Level)", fill="#111827", font=f(36, True))
draw.text((350, 80), "Minimal 6-block flow for presentation and quick explanation", fill="#374151", font=f(20))

nodes = [
    ("Users", "#e0f2fe", "#0284c7"),
    ("Web / Mobile UI", "#fef3c7", "#d97706"),
    ("API Gateway", "#fef3c7", "#d97706"),
    ("Core Service", "#fde68a", "#ca8a04"),
    ("AI Engine", "#ede9fe", "#7c3aed"),
    ("Database", "#dcfce7", "#16a34a"),
]

x = 55
y1, y2 = 180, 320
w, gap = 200, 25
centers = []
for text, fill, stroke in nodes:
    box(x, y1, x + w, y2, text, fill, stroke)
    centers.append((x + w, (y1 + y2) // 2))
    x += w + gap

for i in range(len(centers) - 1):
    x1, y = centers[i]
    x2 = x1 + gap - 8
    arrow(x1 + 4, y, x2, y)

draw.text((530, 390), "Complaint submission -> processing -> intelligence -> storage", fill="#4b5563", font=f(19))

out = "F:/Soykot_podder/AI_Complain_management/docs/block-diagram.png"
img.save(out)
print(f"Generated {out}")
