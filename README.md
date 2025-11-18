# SWU Search App

Simple PyQt5 utility that scans PDFs, shows page previews, and lets you filter/export results.

## Quickstart
- Install deps (from repo root): `pip install .`
- Run the app: `python -m swu_search_app.main` (or `python src/swu_search_app/main.py`)
- Scan PDFs via the UI, then filter and export selected previews.

## Filtering (include/exclude)
- Supports `AND`, `OR`, parentheses, and quoted phrases.
- `*` is a single-character wildcard, but only when inside quotes (e.g., `"0 * 0"` matches `0 1 0` but not `0 12 0`).
- Searches run across extracted text and filenames; include/exclude fields share the same syntax.

## Building an executable
Run `python scripts/build_executable.py <version>` to produce a PyInstaller binary in `./builds` (e.g., `python scripts/build_executable.py 0.2`).

## Where data is stored
Cached scan results are written to the OS app data directory under `swu_search_app/appData.json`.

