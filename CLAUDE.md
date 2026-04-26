# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
pip install -r requirements.txt
python main.py
```

No build step, no test suite, no linter configured. Run the app directly to verify changes.

## Architecture

Two layers with a strict separation: `core/` is pure Python (no PyQt6 imports); `ui/` is PyQt6 only. `MainWindow` (`ui/main_window.py`) is the sole bridge between them.

**Signal flow:**
1. `FilePanel` emits `data_loaded(df, path)` → `MainWindow` classifies columns, populates `VariablePanel`
2. `VariablePanel` emits `analysis_requested(config)` → `MainWindow` runs the core pipeline → pushes results to `CrosstabPanel`, `StatsPanel`, `ChartPanel`

**Core pipeline** (in `MainWindow._on_analysis_requested`):
1. `ResponseConsolidator.apply(df)` — group response categories
2. `CrosstabBuilder.build()` — build contingency table
3. `CrosstabBuilder.format_display()` — convert to renderable `DisplayResult`
4. `StatisticalTester.test()` — select and run appropriate stat test
5. Push results to display panels

## Key design decisions

- **All colors live in `ui/palette.py`** — `APP_STYLESHEET` is an f-string that assembles the global QSS from constants there. Restyling means editing only that file.
- **`_TwoLineCellDelegate`** in `crosstab_panel.py` — paints N and column % in the same table cell. N is the `DisplayRole` value; % is stored in `UserRole`.
- **Statistical tests always use unweighted data** — even when a weight column is active. Weighted counts appear in the table for display only. A note is injected into `StatTestResult.notes` when weights are active.
- **`openpyxl` version pinning** — `!=3.1.0,!=3.1.1` avoids a `synchVertical` bug. `data_loader.py` catches the resulting `TypeError` and re-raises as a `ValueError` with a pip fix message as a fallback.
- **Variable type classification** is heuristic (`variable_classifier.py`) and user-overridable in the UI. The Likert-scale detection (contiguous integers starting at 0 or 1, ending 4–12) is intentional; don't generalize it without understanding the survey context.

## Test data

`testing/generate_survey_data.py` generates synthetic survey data; `testing/survey_test_data.xlsx` is a pre-generated sample for manual testing. Use it to exercise the app after changes.
