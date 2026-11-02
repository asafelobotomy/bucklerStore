# Working on bucklerStore

This repo is the catalog (`catalog/*.yaml` → `index.json`) for
[Buckler](https://github.com/asafelobotomy/buckler) (`~/Projects/buckler`). Sessions here also own
the Buckler code behind store items: opt-in widgets and screensavers. Sessions in the buckler repo
are blocked from changing those files and hand that work to a session here.

## What is ours in Buckler

`~/Projects/buckler/.claude/store-owned.json` lists the files by store id. It covers every
non-standard widget and screensaver, and its tests keep it in step with `index.json`. The guard
(`.claude/store-owned.json`, `.claude/hooks/store_guard.py`, `.claude/settings.json` in buckler) is
ours too. Buckler's project hooks don't load in a session whose project is this repo, so we can
edit those files; Buckler sessions can't.

Shared files stay Buckler's: `MainStage.kt`, `ScreensaverView.kt`, `MainStageScenes.kt`,
`MainStageGlance.kt`, `GlanceWeather.kt`, `MainStagePlayer.kt`, `JellyfinClient.kt`, `Palette.kt`,
and the store's own code (`Store*.kt`, `SettingsStorePane.kt`, `src/buckler/store.py`). Change one
only for a one-line hook-up (a new store item's dispatch case), and say so in the commit.

## Changing a store item's code

1. Work in a worktree of buckler, never its main checkout, which other sessions use:
   `git -C ~/Projects/buckler fetch && git -C ~/Projects/buckler worktree add .claude/worktrees/store-<topic> -b store/<topic> origin/main`,
   then `cp ~/Projects/buckler/launcher/local.properties` into the worktree's `launcher/`.
2. Change only store-owned files, plus a dispatch line in a shared file when a new item needs one.
3. In the worktree: `uv run pytest -q`, `.venv/bin/ruff check src tests scripts .claude/hooks`
   (the main checkout's `.venv`), `uv run python scripts/check_loc.py`, and
   `(cd launcher && ./gradlew :app:testDebugUnitTest :app:lintDebug)`.
4. Raise the item's revision here: in its `catalog/*.yaml` entry set `revision` one higher,
   `changes` to a short line people will read on their TV ("Stone and wood walls, and gems that
   roll the view."), and `requires` to the Buckler version the change ships in: the `version` in
   Buckler's `pyproject.toml` if it has no `v` tag yet, else the next minor version. Rebuild
   `index.json`, copy it over Buckler's two bundled copies in the worktree, and commit both sides.
5. Commit there with what changed and which store item it is. Push or merge only when the user
   says so. Buckler's `main` releases when its version is bumped, so anything on `main` ships next.
6. Remove the worktree and branch once the work is on `main`.

## Adding a store item

1. Here: add it to `catalog/widgets.yaml` or `catalog/screensavers.yaml` (`default: false`,
   `since` and `requires` = the Buckler version it first ships in, `revision: 1`), run
   `uv run python scripts/build_index.py` and `uv run pytest -q`, then commit.
2. In a buckler worktree: add its files to `.claude/store-owned.json` under its id, and copy
   `index.json` over `launcher/app/src/main/assets/store_index.json` and
   `src/buckler/data/store/index.json`. Buckler's tests check all three agree.
3. Push the store change only together with, or after, the Buckler change that ships the item.
   An id older Buckler versions don't know shows as "needs a newer Buckler".

Downloadable colour schemes, fonts and icon packs live only here. Built-in colour schemes are
store-listed (`catalog/schemes.yaml`), but their colours are in Buckler's shared `Palette.kt`.

## Revisions

Every item has a `revision` and a `changes` line; Buckler uses them to tell people an item they
use was updated. Raise the revision for any change people would notice: colours, font or APK
files, or the item's code in Buckler. A new description alone needs none. `build_index.py`
refuses a changed item with the same revision, or a lower one.
