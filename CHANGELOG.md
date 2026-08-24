# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [Unreleased]

### Added

- Documentation site (MkDocs Material, deployed to GitHub Pages via
  `.github/workflows/docs.yml`) with an auto-generated API reference
  (mkdocstrings), pages for network building / robustness / comparisons,
  and a demo page.
- `benchmarks/generate_figures.py`: generates the figures used in the README
  and docs site from the real fixture data, so they can't drift out of sync
  with the code.
- `Notebooks/centerline.ipynb` rewritten to actually run against the real
  fixture (it previously referenced a `Road.shp` that didn't exist in the
  repo); CI now executes it on every push so it can't go stale again.

## [0.2.0] - 2026-08-24

### Added

- `build_network()` / `to_networkx()`: snap centerline endpoints that share a
  junction into a connected edges/nodes graph, instead of disconnected
  per-polygon lines. `process_file(..., build_network=True)` and the CLI's
  `--build-network`/`--snap-tolerance` flags wire this into file I/O,
  handling the metric-CRS-vs-output-CRS distinction automatically.
- `repair_invalid` (default on): auto-repairs invalid input polygons via
  `shapely.make_valid` before processing.
- `on_error="skip"`: drops a genuinely unusable input row (and logs it)
  instead of failing the whole batch; `on_error="raise"` (default) preserves
  the original fail-fast behavior.
- `add_attributes` (default on): adds `length` and `est_width` columns to
  the output.
- `n_jobs`: optional multiprocessing across chunks of the input for large
  batches (the single vectorized `pygeoops.centerline` call remains the
  default at `n_jobs=1`).
- `benchmarks/compare.py`: timing/validity comparison against raw
  `pygeoops.centerline` and the `centerline` (fitodic) package.
- Optional `network` extra (`pip install road-centerline[network]`) for
  `to_networkx()`.

### Fixed

- README no longer implies the package is on PyPI when it wasn't yet.

0.2.0 is the first version published to PyPI. Earlier commits carried a
`0.1.0` version number in `pyproject.toml` for the original implementation
(CRS-aware centerline extraction, vectorized densification, CLI and Python
API) but that version was never tagged or uploaded, so it has no entry here.

[Unreleased]: https://github.com/DBishal13/Road-Centerline/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/DBishal13/Road-Centerline/releases/tag/v0.2.0
