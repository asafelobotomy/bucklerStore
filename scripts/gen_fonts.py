#!/usr/bin/env python3
"""Build the store's fonts from Google Fonts (SIL OFL), as listed in catalog/fonts.yaml.

Each family is fetched from the google/fonts repository at the pinned commit, cut to a Regular
(400) and a Bold (700) instance when it is a variable font, and trimmed to Latin (with the accented
letters of European languages) so a download stays small; Buckler falls back to the system font
for anything else. Output: fonts/<id>/regular.ttf, bold.ttf and the family's OFL.txt.
Run scripts/build_index.py afterwards to pin the new files in index.json.

Usage: uv run python scripts/gen_fonts.py [ID ...]
"""

from __future__ import annotations

import io
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.otlLib.optimize.gpos import compact
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import FONTS_DIR, load_fonts

# Latin, Latin-1, Latin Extended-A/B and Additional (Polish, Czech, Vietnamese…), combining marks,
# general punctuation, currency, letterlike symbols, arrows and the minus sign.
UNICODES = (
    list(range(0x20, 0x250)) + list(range(0x300, 0x370)) + list(range(0x1E00, 0x1F00))
    + list(range(0x2000, 0x2070)) + list(range(0x20A0, 0x20D0)) + list(range(0x2100, 0x2200))
    + [0x2212]
)


def fetch(commit: str, folder: str, name: str) -> bytes:
    url = f"https://raw.githubusercontent.com/google/fonts/{commit}/ofl/{folder}/{urllib.parse.quote(name)}"
    request = urllib.request.Request(url, headers={"User-Agent": "bucklerStore"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def weight(font: TTFont, wght: int) -> TTFont:
    """A static instance of a variable font at [wght], other axes at their defaults."""
    if "fvar" not in font:
        return font
    axes = {a.axisTag: a.defaultValue for a in font["fvar"].axes}
    axes["wght"] = max(min(wght, _axis(font, "wght").maxValue), _axis(font, "wght").minValue)
    if "opsz" in axes:
        # Display sizes on a TV: the optical size meant for large text.
        axes["opsz"] = min(_axis(font, "opsz").maxValue, 32)
    return instancer.instantiateVariableFont(font, axes)


def _axis(font: TTFont, tag: str):
    return next(a for a in font["fvar"].axes if a.axisTag == tag)


def trimmed(font: TTFont) -> bytes:
    options = subset.Options()
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.hinting = False
    options.desubroutinize = True
    options.drop_tables += ["meta"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    # Instancing leaves kerning pairs unpacked; packing them again saves most of their size.
    if "GPOS" in font:
        compact(font, level=9)
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def main(only: list[str]) -> None:
    commit, fonts = load_fonts()
    for font in fonts:
        if only and font["id"] not in only:
            continue
        out = FONTS_DIR / font["id"]
        out.mkdir(parents=True, exist_ok=True)
        source = fetch(commit, font["folder"], font["file"])
        for style, wght in (("regular", 400), ("bold", 700)):
            data = trimmed(weight(TTFont(io.BytesIO(source)), wght))
            (out / f"{style}.ttf").write_bytes(data)
            print(f"{font['id']}/{style}.ttf {len(data) // 1024} KB")
        (out / "OFL.txt").write_bytes(fetch(commit, font["folder"], "OFL.txt"))


if __name__ == "__main__":
    main(sys.argv[1:])
