"""The catalog builds, index.json is current, and every scheme is readable on a TV."""

from __future__ import annotations

import copy
import json
import re

import pytest
from fontTools.ttLib import TTFont

from catalog import (
    BUILT_IN,
    CONTRAST_RULES,
    FONTS_DIR,
    INDEX,
    KINDS,
    CatalogError,
    build,
    check_revisions,
    contrast,
    render,
    validate,
)


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


def test_schemes_have_a_since_version_and_a_prefixed_id() -> None:
    schemes = build()["schemes"]
    assert schemes
    for scheme in schemes:
        assert scheme["id"].startswith("scheme_")
        assert all(part.isdigit() for part in scheme["since"].split("."))


def test_four_schemes_come_standard() -> None:
    standard = {s["id"] for s in build()["schemes"] if s["default"]}
    assert standard == {"scheme_buckler", "scheme_light", "scheme_dark", "scheme_shield"}


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


def test_every_item_has_a_revision_and_built_ins_a_buckler_version() -> None:
    index = build()
    for kind in KINDS:
        for item in index[kind]:
            assert item["revision"] >= 1 and "changes" in item, item["id"]
            if kind in BUILT_IN:
                assert re.fullmatch(r"\d+\.\d+\.\d+", item["requires"]), item["id"]


def test_the_new_maze_is_revision_two_for_buckler_0_23() -> None:
    maze = next(s for s in build()["screensavers"] if s["id"] == "saver_maze")
    assert (maze["revision"], maze["requires"]) == (2, "0.23.0") and maze["changes"]


def test_a_change_without_a_new_revision_is_refused() -> None:
    old = json.loads(render(build()))
    new = copy.deepcopy(old)
    new["themes"][0]["colors"]["brand"] = "#123456"
    with pytest.raises(CatalogError, match="raise its revision"):
        check_revisions(old, new)
    new["themes"][0]["revision"] += 1
    check_revisions(old, new)


def test_a_new_description_alone_needs_no_revision() -> None:
    old = json.loads(render(build()))
    new = copy.deepcopy(old)
    new["widgets"][0]["about"] = "Something clearer."
    check_revisions(old, new)


def test_revisions_never_go_down() -> None:
    old = json.loads(render(build()))
    new = copy.deepcopy(old)
    next(s for s in new["screensavers"] if s["id"] == "saver_maze")["revision"] = 1
    with pytest.raises(CatalogError, match="went down"):
        check_revisions(old, new)


def test_a_later_revision_must_say_what_changed() -> None:
    index = json.loads(render(build()))
    index["fonts"][0].update(revision=2, changes="")
    with pytest.raises(CatalogError, match="changes"):
        validate(index)
