"""Generate original abstract temple-style backgrounds with Python stdlib only."""
import math
from pathlib import Path

PALETTES = [((24, 18, 50), (130, 47, 37), (255, 206, 112)),
            ((9, 42, 62), (17, 104, 106), (255, 222, 142)),
            ((45, 22, 58), (139, 66, 91), (255, 215, 132))]


def render_ppm(path, width=360, height=640, variant=0, prompt="గోపురం దర్శనం"):
    if width < 9 or height < 16:
        raise ValueError("చిత్ర పరిమాణం కనీసం 9×16 ఉండాలి")
    top, bottom, gold = PALETTES[variant % len(PALETTES)]
    pixels = bytearray(width * height * 3)
    for y in range(height):
        amount = y / max(1, height - 1)
        color = tuple(round(a * (1 - amount) + b * amount) for a, b in zip(top, bottom))
        offset = y * width * 3
        pixels[offset:offset + width * 3] = bytes(color) * width

    def rect(x0, y0, x1, y1, color):
        x0, x1 = max(0, int(x0)), min(width, int(x1))
        y0, y1 = max(0, int(y0)), min(height, int(y1))
        row = bytes(color) * max(0, x1 - x0)
        for y in range(y0, y1):
            start = (y * width + x0) * 3
            pixels[start:start + len(row)] = row

    def circle(cx, cy, radius, color):
        for y in range(max(0, int(cy-radius)), min(height, int(cy+radius+1))):
            dx = int(math.sqrt(max(0, radius*radius - (y-cy)**2)))
            rect(cx-dx, y, cx+dx+1, y+1, color)

    circle(width//2, int(height*.31), int(width*.22), gold)
    circle(width//2, int(height*.31), int(width*.18), bottom)
    center, base = width//2, int(height*.82)
    cue = str(prompt)
    if any(word in cue for word in ("దీప", "జ్యోతి", "వెలుగు")):
        # Original lamp motif: glowing flame and a stepped brass bowl.
        circle(center, int(height*.57), int(width*.045), (255, 238, 171))
        circle(center, int(height*.62), int(width*.075), gold)
        rect(center-int(width*.18), int(height*.68), center+int(width*.18), int(height*.72), gold)
        rect(center-int(width*.14), int(height*.72), center+int(width*.14), int(height*.77), (202, 139, 61))
        rect(center-int(width*.08), int(height*.77), center+int(width*.08), int(height*.82), gold)
    elif any(word in cue for word in ("పుష్ప", "పద్మ", "తామర")):
        # Petal rings make a stylized lotus without copying a third-party image.
        cy, radius = int(height*.64), int(width*.11)
        for angle in range(0, 360, 45):
            x = center + int(math.cos(math.radians(angle))*radius)
            y = cy + int(math.sin(math.radians(angle))*radius)
            circle(x, y, int(width*.055), (255, 194, 163))
        circle(center, cy, int(width*.065), gold)
    elif any(word in cue for word in ("కొండ", "పర్వత", "తిరుమల", "గిరి")):
        for offset, color in ((0, (51, 43, 71)), (int(height*.07), (39, 52, 73)), (int(height*.14), (34, 64, 75))):
            ridge = int(height*.64) + offset
            for y in range(ridge, min(height, ridge + int(height*.17))):
                spread = int((y-ridge) * width / max(1, height*.34))
                rect(center-spread, y, center+spread, y+1, color)
        circle(center, int(height*.38), int(width*.11), gold)
    elif any(word in cue for word in ("గ్రంథ", "శ్లోక", "పుస్తక", "పారాయణ")):
        rect(int(width*.2), int(height*.55), int(width*.8), int(height*.8), gold)
        rect(int(width*.24), int(height*.57), center-2, int(height*.77), (248, 225, 177))
        rect(center+2, int(height*.57), int(width*.76), int(height*.77), (236, 211, 162))
        rect(center-1, int(height*.57), center+1, int(height*.78), (104, 57, 49))
        for y in range(int(height*.61), int(height*.75), max(3, height//80)):
            rect(int(width*.28), y, center-int(width*.04), y+1, (150, 112, 81))
            rect(center+int(width*.04), y, int(width*.72), y+1, (150, 112, 81))
    else:
        for tier, (half, tall) in enumerate(((.22, .07), (.17, .065), (.12, .06), (.075, .055))):
            y1 = base - tier * int(height*.06)
            y0 = y1 - int(height*tall)
            for y in range(max(0, y0), min(height, y1)):
                half_width = int(width*half * (y-y0) / max(1, y1-y0))
                rect(center-half_width, y, center+half_width+1, y+1, gold)
        rect(width*.28, base, width*.72, height, (31, 24, 43))
        rect(width*.43, height*.7, width*.57, height, gold)
        for x in (int(width*.17), int(width*.83)):
            circle(x, int(height*.74), max(2, width//45), (255, 225, 153))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        stream.write(pixels)
    return path
