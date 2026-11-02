"""Reading catalog/*.yaml and turning it into index.json, the one file Buckler reads."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
FONTS_DIR = ROOT / "fonts"
INDEX = ROOT / "index.json"

REPO = "asafelobotomy/bucklerStore"
# Files are fetched from main; each is pinned by its sha256, so a changed file is refused rather
# than installed until index.json is rebuilt with it.
RAW = f"https://raw.githubusercontent.com/{REPO}/main"

SCHEMA = 1
KINDS = ("widgets", "screensavers", "schemes", "themes", "fonts", "iconpacks")
# Items whose code or colours ship inside Buckler; `requires` is the Buckler version that carries
# their current revision.
BUILT_IN = ("widgets", "screensavers", "schemes")
COLOR_KEYS = (
    "bgTop", "bgMid", "bgBottom", "brand", "onBrand", "text", "muted", "hint",
    "section", "tile", "footer", "border", "ring",
)
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class CatalogError(ValueError):
    """A catalog file that Buckler could not use."""


def _yaml(name: str) -> dict[str, Any]:
    raw = yaml.safe_load((CATALOG / name).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CatalogError(f"{name}: expected a mapping")
    return raw


def load_fonts() -> tuple[str, list[dict[str, str]]]:
    raw = _yaml("fonts.yaml")
    return str(raw["commit"]), list(raw["fonts"])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CatalogError(f"{path.relative_to(ROOT)} is missing: run scripts/gen_fonts.py")
    return {
        "url": f"{RAW}/{path.relative_to(ROOT).as_posix()}",
        "sha256": sha256(path),
        "size": path.stat().st_size,
    }


def build() -> dict[str, Any]:
    """The index as Buckler reads it, from the catalog and the font files on disk."""
    _, fonts = load_fonts()
    index = {
        "schema": SCHEMA,
        "widgets": [
            {**{k: w[k] for k in ("id", "label", "about", "default", "since", "requires")}, **_revision(w)}
            for w in _yaml("widgets.yaml")["widgets"]
        ],
        "screensavers": [
            {**{k: v[k] for k in ("id", "label", "about", "default", "since", "requires")}, **_revision(v)}
            for v in _yaml("screensavers.yaml")["screensavers"]
        ],
        "schemes": [
            {**{k: v[k] for k in ("id", "label", "about", "default", "since", "requires")}, **_revision(v)}
            for v in _yaml("schemes.yaml")["schemes"]
        ],
        "themes": [
            {"id": t["id"], "label": t["label"], "about": t["about"], **_revision(t), "dark": t["dark"],
             "colors": {k: t["colors"][k].upper() for k in COLOR_KEYS}}
            for t in _yaml("themes.yaml")["themes"]
        ],
        "fonts": [
            {"id": f["id"], "label": f["label"], "about": f["about"], **_revision(f), "license": "OFL-1.1",
             "files": {style: _file(FONTS_DIR / f["id"] / f"{style}.ttf") for style in ("regular", "bold")}}
            for f in fonts
        ],
        "iconpacks": [
            {**{k: str(p[k]) if k != "size" else int(p[k])
                for k in ("id", "label", "package", "version", "url", "sha256", "size", "license", "about")},
             **_revision(p)}
            for p in _yaml("iconpacks.yaml")["iconpacks"]
        ],
    }
    validate(index)
    return index


def _revision(item: dict[str, Any]) -> dict[str, Any]:
    """An item's own revision (1, 2, …) and what changed in the latest one."""
    return {"revision": item["revision"], "changes": str(item.get("changes", ""))}


def check_revisions(old: dict[str, Any], new: dict[str, Any]) -> None:
    """Refuse an item that changed without a higher revision, or whose revision went down.

    Buckler tells people an item they use was updated by comparing revisions, so a change that
    keeps its revision would go unnoticed, and a lower one would look like a downgrade.
    """
    def items(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {i["id"]: i for kind in KINDS for i in index.get(kind, [])}

    before = items(old)
    for ident, item in items(new).items():
        prior = before.get(ident)
        if prior is None or "revision" not in prior:
            continue
        if item["revision"] < prior["revision"]:
            raise CatalogError(f"{ident}: revision went down from {prior['revision']} to {item['revision']}")
        same = {k: v for k, v in item.items() if k not in ("revision", "changes", "about")} == \
            {k: v for k, v in prior.items() if k not in ("revision", "changes", "about")}
        if not same and item["revision"] == prior["revision"]:
            raise CatalogError(f"{ident} changed: raise its revision to {item['revision'] + 1} and say what changed")


def render(index: dict[str, Any]) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def validate(index: dict[str, Any]) -> None:
    seen: set[str] = set()
    for kind in KINDS:
        for item in index[kind]:
            ident = item["id"]
            if not ID.match(ident):
                raise CatalogError(f"{kind}: bad id {ident!r}")
            if ident in seen:
                raise CatalogError(f"{kind}: id {ident!r} is used twice")
            seen.add(ident)
            if not str(item.get("label", "")).strip() or not str(item.get("about", "")).strip():
                raise CatalogError(f"{ident}: needs a label and an about line")
            revision = item.get("revision")
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
                raise CatalogError(f"{ident}: revision must be a whole number from 1")
            if revision > 1 and not item.get("changes", "").strip():
                raise CatalogError(f"{ident}: revision {revision} needs a `changes` line saying what is new")
            if kind in BUILT_IN:
                since, requires = _semver(item["since"], ident), _semver(item["requires"], ident)
                if requires < since:
                    raise CatalogError(f"{ident}: requires {item['requires']} is older than since {item['since']}")
    for theme in index["themes"]:
        for key, value in theme["colors"].items():
            if not HEX.match(value):
                raise CatalogError(f"theme {theme['id']}: {key} {value!r} is not #RRGGBB")
    for pack in index["iconpacks"]:
        if not pack["url"].startswith("https://") or not re.fullmatch(r"[0-9a-f]{64}", pack["sha256"]):
            raise CatalogError(f"icon pack {pack['id']}: needs an https url and a lower-case hex sha256")


def _semver(raw: str, ident: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(raw)):
        raise CatalogError(f"{ident}: {raw!r} is not a version like 0.23.0")
    return tuple(int(part) for part in str(raw).split("."))


def luminance(hex_color: str) -> float:
    def channel(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# Buckler's own rules for its built-in schemes (AppearanceTest.palettesMeetContrast).
CONTRAST_RULES = (
    ("text", "bgTop", 7.0),
    ("text", "tile", 4.5),
    ("text", "footer", 4.5),
    ("muted", "bgTop", 4.5),
    ("onBrand", "brand", 4.5),
    ("brand", "bgTop", 3.0),
    ("section", "bgTop", 3.0),
    ("hint", "bgTop", 3.0),
)
