from PIL import Image, ImageDraw, ImageFont
import math

W, H = 1600, 600
img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)


def f(size, bold=False):
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def box(x1, y1, x2, y2, text, fill="#e0f2fe", stroke="#0284c7"):
    draw.rounded_rectangle((x1, y1, x2, y2), radius=16, fill=fill, outline=stroke, width=3)
    ft = f(24, True)
    l, t, r, b = draw.textbbox((0, 0), text, font=ft)
    draw.text(((x1 + x2 - (r - l)) // 2, (y1 + y2 - (b - t)) // 2), text, fill="#111827", font=ft)


def arrow(x1, y1, x2, y2):
    draw.line((x1, y1, x2, y2), fill="#4b5563", width=5)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 14
    p1 = (x2 - size * math.cos(angle - 0.45), y2 - size * math.sin(angle - 0.45))
    p2 = (x2 - size * math.cos(angle + 0.45), y2 - size * math.sin(angle + 0.45))
    draw.polygon([(x2, y2), p1, p2], fill="#4b5563")


draw.text((580, 25), "Ticket Lifecycle", fill="#111827", font=f(42, True))
draw.text((420, 80), "From customer complaint to closure and learning feedback", fill="#374151", font=f(22))

states = [
    ("Open", "#dbeafe", "#2563eb"),
    ("Assigned", "#fef3c7", "#d97706"),
    ("In Progress", "#fde68a", "#ca8a04"),
    ("Under Review", "#e9d5ff", "#9333ea"),
    ("Resolved", "#dcfce7", "#16a34a"),
    ("Closed", "#ccfbf1", "#0f766e"),
]

x = 70
y = 220
w = 220
h = 110
gap = 35

centers = []
for name, fill, stroke in states:
    box(x, y, x + w, y + h, name, fill=fill, stroke=stroke)
    centers.append((x + w, y + h // 2))
    x += w + gap

for i in range(len(centers) - 1):
    x1, y1 = centers[i]
    x2 = x1 + gap - 8
    arrow(x1 + 5, y1, x2, y1)

# Reopen loop (Closed -> In Progress)
draw.arc((1080, 150, 1530, 480), start=30, end=290, fill="#ef4444", width=4)
arrow(1170, 470, 980, 360)
draw.text((1260, 405), "Reopen", fill="#ef4444", font=f(20, True))

# AI enrichment note
note_x1, note_y1, note_x2, note_y2 = 430, 390, 980, 520
draw.rounded_rectangle((note_x1, note_y1, note_x2, note_y2), radius=12, fill="#f9fafb", outline="#d1d5db", width=2)
draw.text((460, 420), "AI Enrichment runs during lifecycle:", fill="#111827", font=f(20, True))
draw.text((460, 455), "- Classification  - Priority  - Sentiment  - Routing", fill="#374151", font=f(18))
draw.text((460, 482), "- Notifications and SLA timers update at each transition", fill="#374151", font=f(18))

out = "F:/Soykot_podder/AI_Complain_management/docs/ticket-lifecycle.png"
img.save(out)
print(f"Generated {out}")
