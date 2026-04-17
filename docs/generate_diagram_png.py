from PIL import Image, ImageDraw, ImageFont


W, H = 1400, 800
img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)


def font(size, bold=False):
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def rect(x1, y1, x2, y2, fill, outline, text, fs=22, bold=True):
    draw.rounded_rectangle((x1, y1, x2, y2), radius=12, fill=fill, outline=outline, width=3)
    f = font(fs, bold=bold)
    tw, th = draw.textbbox((0, 0), text, font=f)[2:]
    tx = (x1 + x2 - tw) // 2
    ty = (y1 + y2 - th) // 2
    draw.text((tx, ty), text, fill="#111827", font=f)


def db(cx, cy, rx, ry, text):
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill="#dcfce7", outline="#16a34a", width=3)
    f = font(24, bold=True)
    tw, th = draw.textbbox((0, 0), text, font=f)[2:]
    draw.text((cx - tw // 2, cy - th // 2), text, fill="#111827", font=f)


def arrow(x1, y1, x2, y2):
    draw.line((x1, y1, x2, y2), fill="#4b5563", width=4)
    # simple arrow head
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return
    import math
    ang = math.atan2(dy, dx)
    l = 12
    a1 = ang + 2.6
    a2 = ang - 2.6
    p1 = (x2 + l * math.cos(a1), y2 + l * math.sin(a1))
    p2 = (x2 + l * math.cos(a2), y2 + l * math.sin(a2))
    draw.polygon([(x2, y2), p1, p2], fill="#4b5563")


# title
draw.text((420, 20), "AI Complaint Management - System Design", fill="#1f2937", font=font(34, bold=True))

# group boxes
draw.rounded_rectangle((40, 90, 320, 710), radius=14, fill="#f9fafb", outline="#d1d5db", width=3)
draw.rounded_rectangle((370, 90, 840, 710), radius=14, fill="#f9fafb", outline="#d1d5db", width=3)
draw.rounded_rectangle((890, 90, 1360, 710), radius=14, fill="#f9fafb", outline="#d1d5db", width=3)

draw.text((145, 105), "Users", fill="#111827", font=font(24, bold=True))
draw.text((520, 105), "Application Layer", fill="#111827", font=font(24, bold=True))
draw.text((1000, 105), "Backend & Data Layer", fill="#111827", font=font(24, bold=True))

# users
rect(80, 170, 280, 250, "#e0f2fe", "#0284c7", "Admin")
rect(80, 310, 280, 390, "#e0f2fe", "#0284c7", "Customer")
rect(80, 450, 280, 530, "#e0f2fe", "#0284c7", "Support Agent")

# app
rect(430, 170, 780, 250, "#fef3c7", "#d97706", "Web / Mobile UI")
rect(430, 290, 780, 370, "#fef3c7", "#d97706", "API Gateway")
rect(430, 410, 780, 500, "#fef3c7", "#d97706", "Complaint Management Service")
rect(430, 540, 780, 650, "#fef3c7", "#d97706", "AI Engine", fs=24)
draw.text((485, 605), "Classification + Priority + Sentiment", fill="#374151", font=font(18))

# backend
rect(950, 170, 1300, 250, "#e0f2fe", "#0284c7", "Application Server")
rect(950, 290, 1300, 370, "#e0f2fe", "#0284c7", "Message Queue")
db(1125, 465, 175, 42, "Database")
db(1125, 600, 175, 42, "Vector DB")

# arrows
arrow(280, 210, 430, 210)
arrow(280, 350, 430, 210)
arrow(280, 490, 430, 210)
arrow(605, 250, 605, 290)
arrow(605, 370, 605, 410)
arrow(605, 500, 605, 540)
arrow(780, 340, 950, 340)
arrow(780, 455, 950, 210)
arrow(780, 455, 950, 465)
arrow(780, 595, 950, 600)

img.save("F:/Soykot_podder/AI_Complain_management/docs/system-design-diagram.png")
print("Generated docs/system-design-diagram.png")
