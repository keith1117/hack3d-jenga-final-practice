from pathlib import Path
import cadquery as cq

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "solution"
print("Reading the STEP assembly. This can take a few minutes.", flush=True)
assembly = cq.Assembly.load(str(ROOT / "Jenga-Nyasbro.STEP"))
# In this file, assembly instance NAUO48 refers to numbered part 55.
house = assembly.objects["NAUO48"].obj
if isinstance(house, cq.Workplane):
    house = house.val()
cq.exporters.export(house, str(OUT / "models/hidden_house_55.stl"))
cq.exporters.export(house, str(OUT / "models/hidden_house_55.step"))
svg = cq.exporters.getSVG(house, opts={"width": 800, "height": 650,
    "projectionDir": (0, 0, 1), "showHidden": False})
(OUT / "figures/house_front.svg").write_text(svg)
print("Saved the house models and front view.")
