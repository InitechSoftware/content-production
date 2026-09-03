from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 1200, 675
BG = (23, 19, 41)
PANEL = (36, 31, 60)
PURPLE = (107, 78, 255)
LILAC = (201, 186, 255)
GREEN = (37, 211, 102)
WHITE = (255, 255, 255)
MUTED = (200, 194, 220)
LINE = (81, 73, 105)


def font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(name, size)


def rounded(draw, box, radius=22, fill=PANEL, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, value, size, fill=WHITE, bold=False, anchor=None):
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor=anchor)


def arrow(draw, start, end, fill=PURPLE, width=7):
    draw.line([start, end], fill=fill, width=width)
    x, y = end
    draw.polygon([(x, y), (x - 15, y - 10), (x - 15, y + 10)], fill=fill)


def render_cover():
    img = Image.new("RGB", (W, H), BG)  # type: ignore[arg-type]
    d = ImageDraw.Draw(img)
    d.ellipse((790, -180, 1270, 300), fill="#2d2250")
    text(d, (60, 47), "Keep your WhatsApp number", 48, bold=True)
    text(d, (60, 108), "Choose the right connection path before linking GoHighLevel", 25, fill=MUTED)

    rounded(d, (60, 218, 330, 505), outline="#4a4262", width=2)
    d.ellipse((140, 260, 250, 370), fill=GREEN)
    text(d, (195, 315), "WA", 33, bold=True, anchor="mm")
    text(d, (195, 414), "Existing number", 26, bold=True, anchor="mm")
    text(d, (195, 455), "Keep the identity", 19, fill=MUTED, anchor="mm")

    rounded(d, (465, 218, 735, 505), fill="#2b2050", outline=PURPLE, width=3)
    d.ellipse((545, 260, 655, 370), fill=PURPLE)
    text(d, (600, 315), "T", 42, bold=True, anchor="mm")
    text(d, (600, 414), "TimelinesAI", 27, bold=True, anchor="mm")
    text(d, (600, 455), "QR or Coexistence", 19, fill=LILAC, anchor="mm")

    rounded(d, (870, 218, 1140, 505), outline="#4a4262", width=2)
    d.ellipse((950, 260, 1060, 370), fill="#3185fc")
    text(d, (1005, 315), "GHL", 27, bold=True, anchor="mm")
    text(d, (1005, 414), "One sub-account", 25, bold=True, anchor="mm")
    text(d, (1005, 455), "Verify the location", 19, fill=MUTED, anchor="mm")

    arrow(d, (340, 360), (450, 360))
    arrow(d, (745, 360), (855, 360))
    rounded(d, (60, 565, 1140, 630), radius=18, fill="#211b38", outline="#4a4262")
    text(d, (600, 598), "Same number. Different setup rules. Test before rollout.", 24, bold=True, anchor="mm")
    img.save(OUT / "cover.png", optimize=True)


def render_decision():
    img = Image.new("RGB", (W, H), BG)  # type: ignore[arg-type]
    d = ImageDraw.Draw(img)
    text(d, (60, 42), "QR or WABA Coexistence?", 45, bold=True)
    text(d, (60, 99), "A practical decision guide for an existing WhatsApp number", 24, fill=MUTED)

    rounded(d, (60, 170, 570, 550), outline="#4a4262", width=2)
    d.ellipse((100, 210, 176, 286), fill=PURPLE)
    text(d, (138, 248), "QR", 23, bold=True, anchor="mm")
    text(d, (205, 218), "QR / multidevice", 31, bold=True)
    text(d, (205, 260), "Familiar linked-device model", 20, fill=LILAC)
    bullets = [
        "Regular or Business App",
        "Group sync in TimelinesAI",
        "No Meta Business setup",
        "Phone + reconnect owner needed",
    ]
    for i, line in enumerate(bullets):
        y = 330 + i * 48
        d.ellipse((112, y + 6, 124, y + 18), fill=GREEN)
        text(d, (146, y), line, 21)

    rounded(d, (630, 170, 1140, 550), outline="#4a4262", width=2)
    d.ellipse((670, 210, 746, 286), fill=GREEN)
    text(d, (708, 248), "API", 20, bold=True, anchor="mm")
    text(d, (775, 218), "WABA Coexistence", 31, bold=True)
    text(d, (775, 260), "Business App + Cloud API", 20, fill=LILAC)
    bullets = [
        "Meta eligibility required",
        "Template + 24-hour rules",
        "No group sync via Cloud API",
        "Phone app remains, with limits",
    ]
    for i, line in enumerate(bullets):
        y = 330 + i * 48
        d.ellipse((682, y + 6, 694, y + 18), fill=GREEN)
        text(d, (716, y), line, 21)

    rounded(d, (60, 585, 1140, 640), radius=16, fill="#2b2050", outline=PURPLE, width=2)
    text(d, (600, 612), "Both paths connect through TimelinesAI to one selected GHL sub-account.", 23, bold=True, anchor="mm")
    img.save(OUT / "decision.png", optimize=True)


if __name__ == "__main__":
    render_cover()
    render_decision()
    print(OUT / "cover.png")
    print(OUT / "decision.png")
