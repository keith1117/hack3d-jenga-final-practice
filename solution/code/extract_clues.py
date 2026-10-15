from pathlib import Path
from functools import lru_cache
import csv
import json
import re

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw
from scipy.interpolate import BSpline


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "solution"
FIG = OUT / "figures"
RESULT = OUT / "results"
FIG.mkdir(exist_ok=True)
RESULT.mkdir(exist_ok=True)
text = (ROOT / "Jenga-Nyasbro.STEP").read_text()
entities = {int(k): v for k, v in re.findall(r"#(\d+)\s*=\s*(.*?);", text, re.S)}
refs = {k: [int(n) for n in re.findall(r"#(\d+)", v)] for k, v in entities.items()}

# The source STEP uses inches. I use millimetres for the drawings below.
points = {}
for k, v in entities.items():
    if v.startswith("CARTESIAN_POINT"):
        numbers = re.findall(r"[-+]?\d*\.?\d+(?:E[-+]?\d+)?", v.split("'NONE'")[-1])
        points[k] = np.array([float(n) * 25.4 for n in numbers])


@lru_cache(None)
def vertices(root):
    todo, seen, found = [root], set(), []
    while todo:
        k = todo.pop()
        if k in seen:
            continue
        seen.add(k)
        if entities[k].startswith("VERTEX_POINT"):
            found.append(points[refs[k][0]])
        else:
            todo.extend(refs[k])
    return np.array(found)


def descendants(root, kind):
    todo, seen, found = [root], set(), []
    while todo:
        k = todo.pop()
        if k in seen:
            continue
        seen.add(k)
        if entities[k].startswith(kind):
            found.append(k)
        else:
            todo.extend(refs[k])
    return found


# Match each numbered part to its geometric representation.
bodies = {}
for k, v in entities.items():
    if v.startswith("SHAPE_REPRESENTATION_RELATIONSHIP"):
        shape, brep = refs[k]
        name = re.findall(r"'([^']*)'", entities[shape])[0]
        bodies[int(name)] = refs[brep][0]

inventory = []
for part, body in sorted(bodies.items()):
    p = vertices(body)
    inventory.append({"part": part, "entity": body,
                      "internal_shells": len(refs[body]) - 1,
                      "size_mm": np.round(np.ptp(p, axis=0), 3).tolist()})
with (RESULT / "parts.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["part", "STEP_entity", "internal_shells", "x_mm", "y_mm", "z_mm"])
    for row in inventory:
        writer.writerow([row["part"], row["entity"], row["internal_shells"], *row["size_mm"]])


def edge_lines(root):
    lines = []
    for edge in descendants(root, "EDGE_CURVE"):
        a, b, curve = refs[edge]
        value = entities[curve]
        if value.startswith("B_SPLINE_CURVE_WITH_KNOTS"):
            control = np.array([points[r] for r in refs[curve]])
            degree = int(re.search(r"'NONE'\s*,\s*(\d+)", value)[1])
            match = re.search(r"\.UNSPECIFIED\.,\s*\.F\.,\s*\.F\.,\s*\(([^)]*)\),\s*\(([^)]*)\)", value)
            mult = [int(n) for n in match[1].split(",")]
            knots = np.repeat([float(n) for n in match[2].split(",")], mult)
            spline = BSpline(knots, control, degree)
            lines.append(spline(np.linspace(knots[degree], knots[-degree-1], 60)))
        else:
            lines.append(np.array([points[refs[a][0]], points[refs[b][0]]]))
    return lines


def draw_internal(part, axes, filename, rotate=False):
    lines = []
    for number in part if isinstance(part, list) else [part]:
        if number in [2, 3]:
            # Include open cuts at the shared end of the two URL blocks.
            for line in edge_lines(bodies[number]):
                if line[:, 0].min() >= 12.39 and line[:, 0].max() <= 12.51 and line[:, 1].max() <= 6:
                    lines.append(line)
        else:
            for shell in refs[bodies[number]][1:]:
                lines.extend(edge_lines(shell))
    a, b = axes
    p = np.vstack(lines)
    low, high = p.min(axis=0), p.max(axis=0)
    scale = 18
    size = (int((high[a]-low[a])*scale)+60, int((high[b]-low[b])*scale)+60)
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    for line in lines:
        xy = [(30+(p[a]-low[a])*scale, 30+(high[b]-p[b])*scale) for p in line]
        draw.line(xy, fill="black", width=2)
    if rotate:
        image = image.transpose(Image.Transpose.ROTATE_90)
    image.save(FIG / filename)


draw_internal(2, (1, 2), "url_part_2.png", rotate=True)
draw_internal(3, (1, 2), "url_part_3.png", rotate=True)
draw_internal([2, 3], (1, 2), "url_joined.png", rotate=True)
draw_internal(19, (1, 2), "banknote.png", rotate=True)

# These ten blocks contain the QR pattern. Each pair makes one column.
qr_parts = [15, 16, 21, 22, 27, 28, 33, 34, 39, 40]
polygons = []
for part in qr_parts:
    body = bodies[part]
    inner = np.vstack([vertices(s) for s in refs[body][1:]])
    y = inner[:, 1].min()
    column = round((y - 37.4) / 15)
    # Parts 15 and 16 have the two left-hand finder patterns in reverse order.
    z_shift = {15: -75, 16: 75}.get(part, 0)
    for face in descendants(body, "ADVANCED_FACE"):
        p = vertices(face)
        # Both depths matter: some patches reach the outside of a block.
        if np.ptp(p[:, 1]) > 1e-5 or not y-1e-5 <= p[0, 1] <= y+0.2001:
            continue
        loops = []
        for bound in refs[face][:-1]:
            loop = refs[bound][0]
            polygon = []
            for oriented in refs[loop]:
                edge = refs[oriented][0]
                a, b, _ = refs[edge]
                forward = entities[oriented].strip().endswith(".T. )")
                vertex = a if forward else b
                p = points[refs[vertex][0]]
                polygon.append((p[0] + column*25, p[2] + z_shift))
            loops.append((entities[bound].startswith("FACE_OUTER_BOUND"), polygon))
        polygons.append(loops)

p = np.array([p for loops in polygons for _, loop in loops for p in loop])
left, top = p[:, 0].min(), p[:, 1].max()
scale, margin = 8, 100
size = int(max(np.ptp(p, axis=0))*scale) + 2*margin
raw = Image.new("L", (size, size), 255)
for loops in polygons:
    tile = Image.new("L", raw.size, 255)
    draw = ImageDraw.Draw(tile)
    for outer, loop in sorted(loops, reverse=True):
        draw.polygon([(margin+(x-left)*scale, margin+(top-z)*scale) for x, z in loop],
                     fill=0 if outer else 255)
    raw = ImageChops.darker(raw, tile)
raw.save(FIG / "qr_from_geometry.png")
payload, corners, _ = cv2.QRCodeDetector().detectAndDecode(np.array(raw))
if not payload:
    raise RuntimeError("The reconstructed QR code did not decode.")

# Read the square cells at their centres to remove tiny CAD seam artifacts.
pitch = 25.4 * 0.1041665354330708
origin_x = 25.4 * 0.06520764414931879
origin_z = 25.4 * -3.5379116993804245
matrix = np.zeros((45, 45), dtype=np.uint8)
for row in range(45):
    for col in range(45):
        x = round(margin+(origin_x+(col+.5)*pitch-left)*scale)
        z = round(margin+(top-origin_z+(row+.5)*pitch)*scale)
        matrix[row, col] = raw.getpixel((x, z)) < 128
clean = Image.fromarray((1-np.pad(matrix, 4))*255).resize((1060, 1060), Image.Resampling.NEAREST)
clean.save(FIG / "qr_code.png")
clean_payload = cv2.QRCodeDetector().detectAndDecode(np.array(clean))[0]
if clean_payload != payload:
    raise RuntimeError("The cleaned QR code disagrees with the raw geometry.")
np.savetxt(RESULT / "qr_matrix.csv", matrix, fmt="%d", delimiter=",")

summary = {
    "answer": "Monopoly",
    "numbered_parts": len(bodies),
    "assembly_instances": text.count("NEXT_ASSEMBLY_USAGE_OCCURRENCE"),
    "parts_with_enclosed_cavities": sum(row["internal_shells"] > 0 for row in inventory),
    "qr_parts": qr_parts,
    "qr_payload": payload,
    "qr_clean_decode_matches_raw": clean_payload == payload,
    "url_read_from_parts_2_and_3": "https://www.britannica.com/biography/J-P-Morgan",
    "banknote_part": 19,
    "house_part": 55,
}
(RESULT / "findings.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
