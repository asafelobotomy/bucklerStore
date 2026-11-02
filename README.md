# bucklerStore

Add-ons for [Buckler](https://github.com/asafelobotomy/buckler), the Android TV Home for NVIDIA
SHIELD: **widgets**, **screensavers**, **colour schemes**, **fonts** and **icon packs**.

Buckler reads one file from this repository, [`index.json`](index.json), and offers what it lists:

- on the TV, in **Buckler Settings → bucklerStore**;
- from a computer, with `buckler store list` and `buckler store install <id>`.

| Kind | What installing does |
|---|---|
| Widgets | Adds one of Buckler's Main Stage widgets to Home's choices (removing it hides it again). Their code ships in Buckler itself. |
| Screensavers | Adds one of Buckler's screensavers to Settings → Screensaver and the setup wizard (removing it hides it again). Their code ships in Buckler itself. |
| Colour schemes | Saves the scheme on the TV; it joins Appearance → Colour scheme. |
| Fonts | Downloads Regular and Bold (SIL OFL, trimmed to Latin, ~60 KB each); the font joins Appearance → Font. |
| Icon packs | Downloads the APK and hands it to Android to install; pick it in Appearance → Icons & artwork. |

Every downloaded file is pinned by its SHA-256 in `index.json`; Buckler refuses a file that does
not match, and an icon pack whose package name differs from the one listed.

## Adding something

1. Edit the YAML under [`catalog/`](catalog):
   - `themes.yaml` — a colour scheme. Every colour must pass Buckler's contrast rules
     (body text 7:1 on the background, 4.5:1 on tiles; see `scripts/catalog.py`).
   - `fonts.yaml` — a family from [google/fonts](https://github.com/google/fonts) under `ofl/`,
     then `uv run python scripts/gen_fonts.py <id>`.
   - `iconpacks.yaml` — an open icon pack APK with its sha256.
   - `widgets.yaml` — only when Buckler ships a new Main Stage widget (`id` is its Main Stage name).
   - `screensavers.yaml` — only when Buckler ships a new screensaver (`id` is `saver_` and its name).
2. `uv run python scripts/build_index.py`
3. `uv run pytest -q`, and commit `index.json` with your change.

Buckler also bundles a copy of `index.json` (for offline first starts); refresh it there with each Buckler release.

```bash
uv sync --extra dev
uv run python scripts/build_index.py --check && uv run pytest -q
```

## Licences

Scripts and catalog: MIT ([LICENSE](LICENSE)). Each font is under the SIL Open Font License, with
its licence beside it in `fonts/<id>/OFL.txt`. Icon packs are their authors' own, under the
licences listed in `catalog/iconpacks.yaml`, and are downloaded from their own releases.
