"""The catalog builds, index.json is current, and every scheme is readable on a TV."""

from __future__ import annotations

import json

import pytest
from fontTools.ttLib import TTFont

from catalog import CONTRAST_RULES, FONTS_DIR, INDEX, CatalogError, build, contrast, render, validate


def test_index_is_current() -> None:
    assert INDEX.read_text(encoding="utf-8") == render(build()), "run scripts/build_index.py"


@pytest.mark.parametrize("theme", build()["themes"], ids=lambda t: t["id"])
def test_themes_meet_bucklers_contrast_rules(theme: dict) -> None:
    colors = theme["colors"]
    for fg, bg, minimum in CONTRAST_RULES:
        ratio = contrast(colors[fg], colors[bg])
        assert ratio >= minimum, f"{theme['id']}: {fg} on {bg} is {ratio:.2f}, needs {minimum}"


@pytest.mark.parametrize("theme", build()["themes"], ids=lambda t: t["id"])
def test_dark_flag_matches_background(theme: dict) -> None:
    from catalog import luminance

    assert theme["dark"] == (luminance(theme["colors"]["bgTop"]) < 0.4)


@pytest.mark.parametrize("font", build()["fonts"], ids=lambda f: f["id"])
def test_fonts_are_static_latin_with_a_licence(font: dict) -> None:
    folder = FONTS_DIR / font["id"]
    assert (folder / "OFL.txt").is_file()
    for style in ("regular", "bold"):
        ttf = TTFont(folder / f"{style}.ttf")
        assert "fvar" not in ttf, "Buckler loads static instances only"
        assert ord("é") in ttf.getBestCmap()


def test_widgets_have_a_since_version() -> None:
    for widget in build()["widgets"]:
        assert all(part.isdigit() for part in widget["since"].split("."))


def test_screensavers_have_a_since_version_and_a_prefixed_id() -> None:
    savers = build()["screensavers"]
    assert savers
    for saver in savers:
        assert saver["id"].startswith("saver_")
        assert all(part.isdigit() for part in saver["since"].split("."))


def test_four_screensavers_come_standard() -> None:
    standard = {s["id"] for s in build()["screensavers"] if s["default"]}
    assert standard == {"saver_clock", "saver_photos", "saver_uploaded", "saver_now_playing"}


def test_duplicate_ids_are_refused() -> None:
    index = json.loads(render(build()))
    index["fonts"][0]["id"] = index["themes"][0]["id"]
    with pytest.raises(CatalogError):
        validate(index)


def test_bad_colours_are_refused() -> None:
    index = json.loads(render(build()))
    index["themes"][0]["colors"]["text"] = "white"
    with pytest.raises(CatalogError):
        validate(index)
