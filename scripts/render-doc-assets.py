#!/usr/bin/env python3
"""Render the figures used in README.md.

Each figure is a row of panels: the physical thing, the frame the model actually
received, and the JSON it returned. Run from the project root:

    python3 scripts/render-doc-assets.py
"""
import json
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images"
DATA = ROOT / "test-data"

PANEL = 560          # panel image area, square
GAP = 26
MARGIN = 26
LABEL_H = 46
CAPTION_H = 34

BG = (247, 247, 249)
CARD = (30, 34, 46)
INK = (24, 26, 32)
MUTED = (110, 116, 130)
RULE = (222, 224, 230)

# JSON syntax colours, kept close to a normal editor theme
J_KEY = (130, 190, 255)
J_STR = (160, 220, 170)
J_LIT = (240, 160, 120)
J_PUNC = (150, 156, 172)

MONO = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/HelveticaNeue.ttc"


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


_MEASURE = ImageDraw.Draw(Image.new("RGB", (1, 1)))   # for measuring text off-canvas

F_LABEL = font(SANS, 25, 2)      # medium weight
F_CAPTION = font(SANS, 19)
F_JSON = font(MONO, 17)


def load(name):
    """Load an image, converting .avif through sips if needed."""
    src = DATA / name
    if src.suffix.lower() == ".avif":
        png = src.with_suffix(".png")
        if not png.exists():
            subprocess.run(["sips", "-s", "format", "png", str(src), "--out", str(png)],
                           check=True, capture_output=True)
        src = png
    return Image.open(src).convert("RGB")


def fit_square(img, size, box=None):
    """Crop to square (an explicit box, or centred) then resize."""
    if box:
        img = img.crop(box)
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2,
                    (w + side) // 2, (h + side) // 2))
    return img.resize((size, size), Image.LANCZOS)


def draw_json_panel(obj, size, title_lines=None):
    """A dark card with pretty-printed, lightly syntax-coloured JSON."""
    panel = Image.new("RGB", (size, size), CARD)
    d = ImageDraw.Draw(panel)
    pad = 26
    y = pad
    line_h = 25

    # Wrap long string values so nothing runs off the card.
    chars = (size - 2 * pad) // 10
    lines = []
    lines.append(("punc", "{"))
    items = list(obj.items())
    for i, (k, v) in enumerate(items):
        tail = "," if i < len(items) - 1 else ""
        if isinstance(v, str):
            head = f'  "{k}": '
            body = f'"{v}"{tail}'
            wrapped = textwrap.wrap(body, width=max(20, chars - len(head)))
            lines.append(("kv", (head, wrapped[0] if wrapped else '""', "str")))
            for cont in wrapped[1:]:
                lines.append(("cont", cont))
        else:
            lines.append(("kv", (f'  "{k}": ', f"{json.dumps(v)}{tail}", "lit")))
    lines.append(("punc", "}"))

    for kind, payload in lines:
        if kind == "punc":
            d.text((pad, y), payload, font=F_JSON, fill=J_PUNC)
        elif kind == "cont":
            d.text((pad + 10 * len('  "": '), y), payload, font=F_JSON, fill=J_STR)
        else:
            head, body, bodykind = payload
            d.text((pad, y), head, font=F_JSON, fill=J_KEY)
            d.text((pad + 10 * len(head), y), body, font=F_JSON,
                   fill=J_STR if bodykind == "str" else J_LIT)
        y += line_h

    if title_lines:
        y += 12
        d.line([(pad, y), (size - pad, y)], fill=(60, 66, 82), width=1)
        y += 14
        for t in title_lines:
            d.text((pad, y), t, font=F_CAPTION, fill=(150, 156, 172))
            y += 24
    return panel


def compose(panels, labels, captions, out_name):
    """One row of labelled panels with captions underneath."""
    n = len(panels)
    w = MARGIN * 2 + n * PANEL + (n - 1) * GAP
    h = MARGIN + LABEL_H + PANEL + CAPTION_H + MARGIN
    canvas = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(canvas)

    x = MARGIN
    for panel, label, caption in zip(panels, labels, captions):
        d.text((x, MARGIN + 4), label, font=F_LABEL, fill=INK)
        canvas.paste(panel, (x, MARGIN + LABEL_H))
        d.rectangle([x, MARGIN + LABEL_H, x + PANEL - 1, MARGIN + LABEL_H + PANEL - 1],
                    outline=RULE, width=1)
        d.text((x, MARGIN + LABEL_H + PANEL + 9), caption, font=F_CAPTION, fill=MUTED)
        x += PANEL + GAP

    OUT.mkdir(exist_ok=True)
    canvas.save(OUT / out_name, quality=92)
    print(f"wrote images/{out_name}  {canvas.size[0]}x{canvas.size[1]}")


def hero():
    # Panel 1 zooms the defect so it is not a near-duplicate of the frame in panel 2.
    bench = fit_square(load("pcb-bent-pin.jpg"), PANEL, box=(590, 945, 1490, 1845))
    seen = fit_square(load("pcb-bent-pin-512.jpg"), PANEL)
    verdict = draw_json_panel({
        "pass": False,
        "defect": "bent/misaligned header pins",
        "location": "lower left side of the board, first four pins of the bottom yellow header",
        "severity": "medium",
        "reason": "pins are visibly bent outward and not aligned with the header housing, indicating improper insertion or handling",
    }, PANEL, ["212 s, entirely on the board"])
    compose(
        [bench, seen, verdict],
        ["The board", "What the model saw", "What it returned"],
        ["Four splayed pins on the lower-left header",
         "512 px, the frame sent to the model",
         "No training data, no labels, no cloud"],
        "hero.jpg",
    )


def lumo_voice():
    designed = fit_square(load("3d-pcb.avif"), PANEL)
    built = fit_square(load("pcb-solder-bridge.jpg"), PANEL, box=(743, 378, 2143, 1778))
    verdict = draw_json_panel({
        "pass": False,
        "defect": "excess solder residue, burn marks and possible solder bridging",
        "location": "central-right area around D6, R5, R4 and D4",
        "severity": "high",
    }, PANEL, ["220 s. R4, R5 and D4 are real parts", "in that area. There is no D6."])
    compose(
        [designed, built, verdict],
        ["As designed", "As built", "What it returned"],
        ["LUMO VOICE, the CAD render",
         "The same board, hand-soldered",
         "Right area, one invented designator"],
        "lumo-voice.jpg",
    )


# --------------------------------------------------------------------------------
# Session figures. These are drawn rather than screenshotted, so the text stays sharp
# and legible at documentation size. Every line of content is verbatim from the logs
# in results/; only the layout is designed.
# --------------------------------------------------------------------------------

WIDE = 1400
F_TERM = font(MONO, 19)
F_TERM_B = font(MONO, 19, 1)     # bold face in the Menlo collection
F_UI = font(SANS, 21)
F_UI_B = font(SANS, 21, 2)
F_CHROME = font(MONO, 17)

TERM_BG = (24, 27, 37)
TERM_BAR = (40, 44, 58)
T_DIM = (128, 136, 156)
T_TEXT = (226, 230, 238)
T_PROMPT = (126, 214, 160)
T_USER = (240, 214, 130)
T_STATUS = (140, 190, 255)


def wrap_mono(text, width_chars):
    out = []
    for para in text.split("\n"):
        out.extend(textwrap.wrap(para, width=width_chars) or [""])
    return out


def window(w, h, bar_color, bg_color, title=None, title_font=None, title_color=None):
    """A card with a rounded title bar and three dots."""
    img = Image.new("RGB", (w, h), bg_color)
    d = ImageDraw.Draw(img)
    bar_h = 46
    d.rectangle([0, 0, w, bar_h], fill=bar_color)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([18 + i * 22, 17, 30 + i * 22, 29], fill=c)
    if title:
        tw = d.textlength(title, font=title_font)
        d.text(((w - tw) / 2, 13), title, font=title_font, fill=title_color)
    return img, d, bar_h


def terminal_figure():
    """llama-cli, showing the chain of thought and the speed line it prints."""
    lines = []
    lines.append(("cmd", "$ ./build/bin/llama-cli -m ~/models/muse-glimmer-30B-kquant-17gb.gguf -t 8 -c 4096"))
    lines.append(("blank", ""))
    lines.append(("user", "> In two sentences, what is edge AI and why run a model locally?"))
    lines.append(("blank", ""))
    lines.append(("dim", "[Start thinking]"))
    for l in ["We need two sentences. Probably definition of edge AI and why run model",
              "locally. Ensure two sentences. Could also be one sentence definition + why.",
              "Make sure two sentences. No extra fragments.",
              "..."]:
        lines.append(("dim", l))
    lines.append(("dim", "[End thinking]"))
    lines.append(("blank", ""))
    body = ("Edge AI is the practice of running artificial intelligence models on local "
            "devices like phones, cameras, and sensors instead of in remote cloud data "
            "centers. Running a model locally reduces latency, protects privacy by "
            "keeping data on-device, and enables reliable operation without constant "
            "internet connectivity.")
    for l in wrap_mono(body, 78):
        lines.append(("text", l))
    lines.append(("blank", ""))
    lines.append(("status", "[ Prompt: 7.2 t/s | Generation: 2.7 t/s ]"))

    pad, lh = 30, 28
    h = 46 + pad * 2 + lh * len(lines)
    img, d, bar_h = window(WIDE, h, TERM_BAR, TERM_BG,
                           "ubuntu@iq-9075: ~/llama.cpp", F_CHROME, T_DIM)
    y = bar_h + pad
    colour = {"cmd": T_TEXT, "user": T_USER, "dim": T_DIM,
              "text": T_TEXT, "status": T_STATUS, "blank": T_TEXT}
    for kind, text in lines:
        f = F_TERM_B if kind in ("cmd", "user", "status") else F_TERM
        d.text((pad, y), text, font=f, fill=colour[kind])
        y += lh
    OUT.mkdir(exist_ok=True)
    img.save(OUT / "terminal.png")
    print(f"wrote images/terminal.png  {img.size[0]}x{img.size[1]}")


def browser_figure():
    """The served UI, showing the answer that cited two conflicting sources."""
    q = "Which Wi-Fi and Bluetooth versions does it support?"
    a_lines = [
        ("t", "The Dragonwing IQ-9075 EVK supports:"),
        ("b", ""),
        ("t", "• Wi-Fi: Wi-Fi 6E"),
        ("t", "• Bluetooth: Bluetooth 5.3"),
        ("b", ""),
        ("t", "Device specifications table lists:"),
        ("m", "Wireless: Wi-Fi 6E, Bluetooth 5.3"),
        ("b", ""),
        ("t", "Wi-Fi and Bluetooth interface overview page also specifies:"),
        ("m", "Standard Wi-Fi 6E (802.11ax)"),
        ("m", "Standard Bluetooth Core Specification v5.2"),
    ]
    pad, lh = 34, 32
    # Measure the bubble before drawing so the canvas has no dead space underneath.
    content = sum(12 if k == "b" else lh for k, _ in a_lines)
    h = 46 + 26 + 74 + 20 + content + 8 + 22 + 24 + 30
    img, d, bar_h = window(WIDE, h, (238, 240, 244), (252, 252, 253))

    # URL bar
    d.rounded_rectangle([120, 10, WIDE - 24, 36], radius=13, fill=(255, 255, 255),
                        outline=(214, 218, 226))
    d.text((136, 14), "192.168.2.177:8080", font=F_CHROME, fill=(96, 102, 118))

    y = bar_h + 26
    # user bubble, right aligned
    qw = d.textlength(q, font=F_UI) + 44
    d.rounded_rectangle([WIDE - 30 - qw, y, WIDE - 30, y + 46], radius=14,
                        fill=(228, 236, 252))
    d.text((WIDE - 30 - qw + 22, y + 12), q, font=F_UI, fill=(28, 40, 66))
    y += 74

    # assistant bubble
    box_top = y
    inner = y + 20
    for kind, text in a_lines:
        if kind == "b":
            inner += 12
            continue
        f = F_TERM if kind == "m" else F_UI
        fill = (92, 108, 140) if kind == "m" else (32, 36, 46)
        d.text((52, inner), text, font=f, fill=fill)
        inner += lh
    d.rounded_rectangle([30, box_top, WIDE - 220, inner + 8], radius=14,
                        outline=(224, 227, 234), width=2)
    d.text((52, inner + 22), "80.2 s   •   26,366 of 26,454 tokens already cached",
           font=F_CAPTION, fill=MUTED)

    img.save(OUT / "webui.png")
    print(f"wrote images/webui.png  {img.size[0]}x{img.size[1]}")


def toolcall_figure():
    """Sensor report in, tool call out."""
    pad, lh = 30, 28
    left = [
        ("h", "SENSOR REPORT  (user message)"),
        ("t", "soil moisture 18% (threshold 30%)"),
        ("t", "air temperature 34C"),
        ("t", "humidity 71%"),
        ("t", "time 14:05"),
        ("t", "last watering 2 days ago"),
        ("b", ""),
        ("h", "TOOLS OFFERED"),
        ("t", "run_pump(seconds)"),
        ("t", "set_vent(position)"),
        ("t", "log_observation(text)"),
    ]
    right = [
        ("h", "RESPONSE  finish_reason: tool_calls"),
        ("j", '{'),
        ("j", '  "type": "function",'),
        ("j", '  "function": {'),
        ("j", '    "name": "run_pump",'),
        ("j", '    "arguments": "{\\"seconds\\":120}"'),
        ("j", '  }'),
        ("j", '}'),
        ("b", ""),
        ("c", "205.4 s  •  588 prompt, 354 completion"),
    ]
    rows = max(len(left), len(right))
    h = 46 + pad * 2 + lh * rows + 20
    img, d, bar_h = window(WIDE, h, TERM_BAR, TERM_BG,
                           "POST /v1/chat/completions", F_CHROME, T_DIM)
    colw = WIDE // 2
    d.line([(colw, bar_h + 14), (colw, h - 14)], fill=(52, 58, 76), width=1)

    for col, items in ((0, left), (1, right)):
        y = bar_h + pad
        x = pad + col * colw + (14 if col else 0)
        for kind, text in items:
            if kind == "b":
                y += lh
                continue
            f = F_TERM_B if kind == "h" else F_TERM
            fill = {"h": T_STATUS, "t": T_TEXT, "j": T_PROMPT,
                    "c": T_DIM}.get(kind, T_TEXT)
            d.text((x, y), text, font=f, fill=fill)
            y += lh

    img.save(OUT / "tool-call.png")
    print(f"wrote images/tool-call.png  {img.size[0]}x{img.size[1]}")


# --------------------------------------------------------------------------------
# Concept figures, and the diagram/table renders Hackster needs (it does not render
# mermaid or wide markdown tables).
# --------------------------------------------------------------------------------

def arrow(d, x, y, length=44, colour=(150, 160, 180), width=3):
    """A drawn arrow. The sans font here has no glyph for the arrow character."""
    d.line([(x, y), (x + length, y)], fill=colour, width=width)
    d.polygon([(x + length + 10, y), (x + length - 4, y - 8), (x + length - 4, y + 8)],
              fill=colour)


ACCENT = (44, 102, 214)
ACCENT_2 = (206, 118, 42)
SOFT = (232, 238, 250)
SOFT_2 = (252, 238, 224)


def architecture_figure():
    """What the model is made of, and the attention pattern behind the cheap KV cache."""
    W, H = 1500, 620
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_h = font(SANS, 30, 2)
    f_b = font(SANS, 21)
    f_s = font(SANS, 18)
    f_t = font(MONO, 17)

    d.text((40, 34), "Muse Glimmer 30B, in two halves", font=f_h, fill=INK)

    # Vision encoder
    d.rounded_rectangle([40, 96, 430, 300], radius=16, fill=SOFT_2, outline=(226, 200, 172))
    d.text((66, 122), "Perception encoder", font=font(SANS, 24, 2), fill=(150, 82, 20))
    for i, line in enumerate(["ViT-G/14, ~1.8 B parameters",
                              "50 layers, width 1536",
                              "up to 4096 visual tokens",
                              "ships separately as mmproj"]):
        d.text((66, 168 + i * 30), line, font=f_b, fill=(110, 74, 32))

    arrow(d, 452, 198, length=46, colour=(178, 186, 200))

    # Text tower
    d.rounded_rectangle([510, 96, 1460, 300], radius=16, fill=SOFT, outline=(200, 214, 240))
    d.text((540, 122), "Text tower", font=font(SANS, 24, 2), fill=(28, 66, 150))
    for i, line in enumerate(["52 layers, hidden 6656, SwiGLU 19968",
                              "27.85 B parameters",
                              "GQA 32 query heads / 2 KV heads",
                              "context 131,072   vocab 202,048"]):
        d.text((540, 168 + i * 30), line, font=f_b, fill=(34, 58, 110))

    # Attention pattern band
    d.text((40, 348), "Attention alternates, and that is why long context is cheap here",
           font=font(SANS, 23, 2), fill=INK)
    x, y, bw, bh = 40, 396, 104, 62
    pattern = ["L", "L", "L", "G"] * 3
    for i, kind in enumerate(pattern):
        fill = SOFT if kind == "L" else (44, 102, 214)
        text_fill = (34, 58, 110) if kind == "L" else (255, 255, 255)
        edge = (200, 214, 240) if kind == "L" else (44, 102, 214)
        d.rounded_rectangle([x, y, x + bw - 10, y + bh], radius=9, fill=fill, outline=edge)
        label = "sliding" if kind == "L" else "full"
        tw = d.textlength(label, font=f_s)
        d.text((x + (bw - 10 - tw) / 2, y + 20), label, font=f_s, fill=text_fill)
        x += bw
    d.text((x + 14, y + 20), "...  x13", font=f_s, fill=MUTED)

    for i, line in enumerate([
        "Three of every four layers see only a 2,048-token window, and use RoPE.",
        "Every fourth layer sees everything, and uses no positional encoding at all.",
        "Result: a full 131,072-token context costs about 1.8 GB of KV cache, not tens of GB.",
    ]):
        d.text((40, 500 + i * 30), line, font=f_b, fill=(64, 70, 84))

    OUT.mkdir(exist_ok=True)
    img.save(OUT / "architecture.png")
    print(f"wrote images/architecture.png  {W}x{H}")


def cadence_figure():
    """Every measured job on one log scale. Reflexes and deliberation are different worlds."""
    import math
    W, H = 1500, 600
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 30), "One board, two very different clocks", font=font(SANS, 30, 2), fill=INK)
    d.text((40, 74), "Every figure below is measured on this hardware. The scale is logarithmic.",
           font=font(SANS, 20), fill=MUTED)

    x0, x1, axis_y = 100, W - 90, 356
    band_top, band_bot = 132, 424
    lo, hi = math.log10(0.004), math.log10(6000)

    def px(seconds):
        return x0 + (math.log10(seconds) - lo) / (hi - lo) * (x1 - x0)

    # Tinted columns behind everything, so labels never fight the bands.
    d.rectangle([x0 - 40, band_top, px(0.5), band_bot], fill=(233, 245, 236))
    d.rectangle([px(8), band_top, x1 + 40, band_bot], fill=(235, 240, 251))
    # Band captions sit at the foot of each column; the space above belongs to labels.
    d.text((x0 - 28, band_bot - 34), "REFLEX  ·  Hexagon NPU",
           font=font(SANS, 19, 2), fill=(40, 116, 66))
    d.text((px(8) + 16, band_bot - 34), "DELIBERATION  ·  CPU, this guide",
           font=font(SANS, 19, 2), fill=(36, 68, 152))

    d.line([(x0 - 40, axis_y), (x1 + 40, axis_y)], fill=(186, 192, 206), width=2)
    for tick, label in [(0.01, "10 ms"), (0.1, "100 ms"), (1, "1 s"), (10, "10 s"),
                        (60, "1 min"), (600, "10 min"), (3600, "1 hour")]:
        tx = px(tick)
        d.line([(tx, axis_y - 6), (tx, axis_y + 6)], fill=(168, 174, 190), width=2)
        tw = d.textlength(label, font=font(SANS, 17))
        d.text((tx - tw / 2, axis_y + 13), label, font=font(SANS, 17), fill=MUTED)

    # (seconds, headline, detail, colour, side, tier) with explicit stagger levels so
    # nothing collides on a log axis where 205 s and 212 s are the same place.
    events = [
        (0.006, "YOLOv11 detection", "6 ms  (earlier guide)", (40, 122, 68), -1, 0),
        (34.0, "encode one image", "34 s", ACCENT, -1, 0),
        (80, "question, document already read", "51 to 134 s", ACCENT, 1, 0),
        (210, "inspection verdict, and a tool call", "212 s  /  205 s", ACCENT, -1, 1),
        (3999, "read a 26,000-token manual", "3,999 s", ACCENT_2, 1, 1),
    ]
    f_head = font(SANS, 19, 2)
    f_det = font(SANS, 18)
    for secs, head, detail, colour, side, level in events:
        ex = px(secs)
        up = side < 0
        stem = 92 + level * 62 if up else 96 + level * 62
        ey = axis_y - stem if up else axis_y + stem
        d.line([(ex, axis_y), (ex, ey)], fill=colour, width=2)
        d.ellipse([ex - 6, axis_y - 6, ex + 6, axis_y + 6], fill=colour)
        wmax = max(d.textlength(head, font=f_head), d.textlength(detail, font=f_det))
        tx = min(max(ex - wmax / 2, 14), W - wmax - 14)
        ty = ey - 50 if up else ey + 6
        d.text((tx, ty), head, font=f_head, fill=colour)
        d.text((tx, ty + 25), detail, font=f_det, fill=MUTED)

    d.text((40, H - 42),
           "Reflexes run at frame rate and never block. Deliberation wakes only for things worth thinking about.",
           font=font(SANS, 20), fill=(64, 70, 84))
    img.save(OUT / "cadence.png")
    print(f"wrote images/cadence.png  {W}x{H}")


def two_tier_figure():
    """The mermaid diagram, rendered for places that do not draw mermaid."""
    W, H = 1500, 560
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_h = font(SANS, 26, 2)
    f_b = font(SANS, 20)
    f_s = font(SANS, 17)

    d.text((40, 28), "Two tiers, one board", font=font(SANS, 30, 2), fill=INK)

    def box(x, y, w, h, title, sub, fill, outline, tcol):
        d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill, outline=outline, width=2)
        d.text((x + 20, y + 18), title, font=f_b, fill=tcol)
        if sub:
            d.text((x + 20, y + 46), sub, font=f_s, fill=MUTED)

    # reflex row
    d.rounded_rectangle([30, 86, W - 30, 246], radius=16, fill=(238, 248, 241),
                        outline=(206, 230, 214), width=2)
    d.text((52, 100), "REFLEX TIER    Hexagon NPU, milliseconds", font=f_h, fill=(38, 110, 62))
    box(52, 142, 380, 86, "Camera or sensors", "continuous", (255, 255, 255), (206, 230, 214), INK)
    box(500, 142, 420, 86, "Detector or classifier", "6 ms per frame", (255, 255, 255), (206, 230, 214), INK)
    box(988, 142, 460, 86, "Immediate reaction", "stop, avoid, count, alarm", (255, 255, 255), (206, 230, 214), INK)
    for ax in (446, 934):
        arrow(d, ax, 185, length=40, colour=(120, 170, 140))

    # deliberation row
    d.rounded_rectangle([30, 318, W - 30, 478], radius=16, fill=(236, 241, 252),
                        outline=(206, 218, 242), width=2)
    d.text((52, 332), "DELIBERATION TIER    CPU, minutes", font=f_h, fill=(34, 66, 150))
    box(52, 374, 380, 86, "Situation summary", "on an interesting event", (255, 255, 255), (206, 218, 242), INK)
    box(500, 374, 420, 86, "Muse Glimmer", "reason, decide, call tools", (255, 255, 255), (206, 218, 242), INK)
    box(988, 374, 460, 86, "Plan, verdict, log entry", "handed back", (255, 255, 255), (206, 218, 242), INK)
    for ax in (446, 934):
        arrow(d, ax, 417, length=40, colour=(120, 145, 200))

    # Linking arrows, routed through the gap between the bands so neither crosses a box.
    link = (150, 160, 180)
    d.line([(660, 232), (660, 366)], fill=link, width=2)
    d.polygon([(660, 374), (653, 362), (667, 362)], fill=link)          # down into deliberation
    d.text((674, 284), "interesting event", font=f_s, fill=MUTED)

    d.line([(1218, 374), (1218, 292), (770, 292), (770, 244)], fill=link, width=2)
    d.polygon([(770, 234), (763, 246), (777, 246)], fill=link)          # up into the detector
    d.text((880, 262), "new goal or setting", font=f_s, fill=MUTED)

    d.text((40, 508),
           "A planner that thinks for a few minutes is ordinary. A brake that thinks for a few minutes is not.",
           font=font(SANS, 20), fill=(64, 70, 84))
    img.save(OUT / "two-tier.png")
    print(f"wrote images/two-tier.png  {W}x{H}")


# Every markdown table in README.md is rendered from the README itself, so the images
# can never drift from the prose. Keyed by the table's header row.
TABLE_SPECS = {
    ("Term", "Meaning"): dict(
        out="terms-table.png", title="Terms used in this guide", wrap=58),
    ("What", "Time"): dict(
        out="inspection-timing.png", title="What one inspection costs", wrap=46),
    ("Context", "KV cache"): dict(
        out="kv-cache-table.png", title="Why a 131K context is affordable here", wrap=46),
    ("Step", "Tokens", "Time"): dict(
        out="document-timing.png", title="Read the document once, then ask", wrap=30,
        note="The first call pays for the whole document. Every question after reuses the cache."),
    ("Threads", "Prefill (512 tokens)", "Generation (64 tokens)"): dict(
        out="threads-table.png", title="Use all eight cores", wrap=26),
    ("Tier", "Runs on", "Timescale", "Good for"): dict(
        out="tiers-table.png", title="Which tier a job belongs to", wrap=34),
    ("Measurement", "Value"): dict(
        out="results-table.png", title="Measured on the board", wrap=52,
        note="Raw logs for every number are in results/."),
}

# A couple of cells point at their surroundings, which means nothing in a standalone
# image. Reword just those.
CELL_SUBS = {
    "This distinction explains the whole performance story below.":
        "This distinction explains the performance story in this guide.",
}


def parse_markdown_tables(md_path):
    """Yield (headers, rows) for every pipe table in a markdown file."""
    lines = md_path.read_text().splitlines()
    i, tables = 0, []
    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and set(lines[i + 1]) <= set("|-: "):
            block = []
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                block.append(lines[j])
                j += 1
            cells = [[c.strip() for c in row.strip("|").split("|")] for row in block]
            tables.append((cells[0], cells[2:]))   # skip the |---| separator row
            i = j
        else:
            i += 1
    return tables


def render_table(headers, rows, out, title, wrap=48, note=None):
    """Render one parsed markdown table. Bold cells stay bold; long cells wrap."""
    f_head = font(SANS, 20, 2)
    f_cell = font(SANS, 20)
    f_cell_b = font(SANS, 20, 2)
    f_key = font(SANS, 21, 2)
    pad, lh, row_pad = 40, 29, 22

    def clean(cell):
        bold = "**" in cell
        text = cell.replace("**", "").replace("`", "")
        return CELL_SUBS.get(text, text), bold

    grid = [[clean(c) for c in row] for row in rows]
    wrapped = [[(textwrap.wrap(t, width=wrap) or [""], b) for t, b in row] for row in grid]

    ncol = len(headers)
    col_w = []
    for c in range(ncol):
        widest = max(
            [_MEASURE.textlength(headers[c].replace("**", ""), font=f_head)] +
            [_MEASURE.textlength(line, font=f_cell_b)
             for row in wrapped for line in row[c][0]]
        )
        col_w.append(widest + 46)

    W = pad * 2 + int(sum(col_w))
    body_h = sum(max(len(cell[0]) for cell in row) * lh + row_pad for row in wrapped)
    H = 90 + 46 + body_h + (44 if note else 0) + pad

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((pad, 28), title, font=font(SANS, 27, 2), fill=INK)

    y = 96
    x = pad
    for h, w in zip(headers, col_w):
        d.text((x, y), h.replace("**", ""), font=f_head, fill=(60, 68, 86))
        x += w
    y += 32
    d.line([(pad, y), (W - pad, y)], fill=(196, 202, 214), width=2)
    y += 14

    for i, row in enumerate(wrapped):
        h = max(len(cell[0]) for cell in row) * lh + row_pad
        emphasised = any(b for _, b in row)
        if emphasised:
            d.rounded_rectangle([pad - 12, y - 8, W - pad + 12, y + h - 14], radius=6,
                                fill=(232, 238, 250))
        elif i % 2 == 0:
            d.rectangle([pad - 12, y - 8, W - pad + 12, y + h - 14], fill=(241, 242, 246))
        x = pad
        for c, (cell_lines, bold) in enumerate(row):
            f = f_key if c == 0 else (f_cell_b if bold else f_cell)
            colour = (28, 62, 140) if c == 0 else (40, 44, 56)
            for j, line in enumerate(cell_lines):
                d.text((x, y + j * lh), line, font=f, fill=colour)
            x += col_w[c]
        y += h
        if i < len(wrapped) - 1 and not emphasised:
            d.line([(pad, y - 12), (W - pad, y - 12)], fill=(228, 231, 238), width=1)

    if note:
        d.text((pad, y + 6), note, font=font(SANS, 18), fill=MUTED)

    OUT.mkdir(exist_ok=True)
    img.save(OUT / out)
    print(f"wrote images/{out}  {W}x{H}")


def all_readme_tables():
    seen = set()
    for headers, rows in parse_markdown_tables(ROOT / "README.md"):
        spec = TABLE_SPECS.get(tuple(headers))
        if spec is None:
            print(f"  WARNING: no spec for table {headers}, skipped")
            continue
        render_table(headers, rows, **spec)
        seen.add(tuple(headers))
    for missing in set(TABLE_SPECS) - seen:
        print(f"  WARNING: spec {missing} matched no table in README.md")


def structure_figure():
    W, H = 1240, 520
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 28), "Project structure", font=font(SANS, 27, 2), fill=INK)
    d.rounded_rectangle([36, 84, W - 36, H - 40], radius=14, fill=CARD)
    f = font(MONO, 19)
    rows = [
        (".", J_PUNC, ""),
        ("├── scripts/", J_KEY, ""),
        ("│   ├── inspect.sh", J_STR, "inspect one image, print a JSON verdict"),
        ("│   ├── manual_qa.py", J_STR, "read a long document once, then ask questions"),
        ("│   ├── fetch-manual.sh", J_STR, "rebuild that document from Qualcomm's pages"),
        ("│   ├── membw.c", J_STR, "the memory-bandwidth probe behind 52 GB/s"),
        ("│   └── render-doc-assets.py", J_STR, "rebuilds every figure in the guide"),
        ("├── results/", J_KEY, "raw logs for every number quoted"),
        ("├── test-data/", J_KEY, "the board photos used in the inspection runs"),
        ("└── images/", J_KEY, "figures used in the guide"),
    ]
    # Comment column starts clear of the longest tree entry, measured not guessed.
    col = 64 + max(d.textlength(t, font=f) for t, _, _ in rows) + 34
    y = 112
    for text, colour, comment in rows:
        d.text((64, y), text, font=f, fill=colour)
        if comment:
            d.text((col, y), comment, font=f, fill=J_PUNC)
        y += 36
    img.save(OUT / "project-structure.png")
    print(f"wrote images/project-structure.png  {W}x{H}")


if __name__ == "__main__":
    hero()
    lumo_voice()
    terminal_figure()
    browser_figure()
    toolcall_figure()
    architecture_figure()
    cadence_figure()
    two_tier_figure()
    all_readme_tables()
    structure_figure()
