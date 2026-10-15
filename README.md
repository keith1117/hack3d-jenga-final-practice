# Hack3D Jenga Final Round Practice

My solution to the 2023 Hack3D final challenge, completed as practice for the 2026 CSAW final round. I am on team **No Fix**.

**My answer is Monopoly.** I recovered a split J. P. Morgan biography URL, reconstructed a QR code leading to a board-game-pieces photo, and found a 500-denomination banknote and a small house model.

## Files

- [Practice report](solution/Jenga_Practice_Report.docx): my process, results, and approaches that did not work.
- [Findings](solution/results/findings.json): recovered links and the QR decoding check.
- [Recovered QR code](solution/figures/qr_code.png) and [original geometric rendering](solution/figures/qr_from_geometry.png).
- [Linked board-game image](solution/clues/game_pieces.png).
- [Banknote](solution/figures/banknote.png), [URL lettering](solution/figures/url_joined.png), and [house view](solution/figures/house_front.svg).
- [House STEP](solution/models/hidden_house_55.step) and [house STL](solution/models/hidden_house_55.stl), extracted from part 55.
- `solution/code/`: the Python scripts.
- The two original assignment files are kept in this folder without changes.

## What I did

I first checked the STEP text and part names. The useful clues were in the geometry rather than readable metadata. I inspected the enclosed shells and thin internal faces, drew the lettering, and combined ten blocks into a QR image. Parts 15 and 16 needed to exchange their positions along the long direction. I also had to include faces at both depths of the pattern, including cuts connected to the outside of the blocks. Using only enclosed cavities left too much of the QR code missing.

The raw geometric QR rendering and the cleaned 45 by 45 cell image decode to the same Google Drive URL. The linked image contains many different board-game pieces, so I treated it as supporting context. The banknote and house are stronger clues for Monopoly. Hasbro's [Monopoly rules](https://www.hasbro.com/common/instruct/Monopoly_Vintage.pdf) also list $500 bills, houses, and hotels. This is my conclusion from the clues, rather than an official answer key.

## Run the scripts

I used Python 3.12. From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r solution/code/requirements.txt
python solution/code/extract_clues.py
```

This regenerates the URL, banknote, and QR drawings, the part inventory, QR matrix, and findings. It does not need a network connection after the packages are installed. The small STEP parser is written for this supplied file; it is not a general STEP reader.

To re-export the house from the original STEP assembly:

```bash
python solution/code/export_house.py
```

Reading the full CAD assembly can take a few minutes. The script saves STEP, STL, and an SVG front view. The PNG front view in the report is a raster copy of that SVG.

To rebuild the Word report from the saved figures:

```bash
python solution/code/build_report.py
```

The image linked by the QR code was downloaded from:

```text
https://drive.google.com/file/d/1INetMAmWu2S0kqHK8zMEVcYfBpoYQ0bC/view?usp=sharing
```

Its original PNG is saved locally so the report does not depend on the link staying available. File hashes and the image's source URL are in `solution/results/source_files.json`.

The supplied challenge files and linked image remain their respective owners' materials. This repository records my practice work; it does not add a license to those source materials.
