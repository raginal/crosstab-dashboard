# Survey Crosstab Analyzer — Technical Documentation

## Table of Contents
1. [Overview](#1-overview)
2. [Installation and Running](#2-installation-and-running)
3. [Architecture](#3-architecture)
4. [Core Modules](#4-core-modules)
5. [UI Modules](#5-ui-modules)
6. [Statistical Logic](#6-statistical-logic)
7. [Customizing Colors](#7-customizing-colors)

---

## 1. Overview

A local desktop application (PyQt6) for contingency table analysis of survey data. All processing runs on the analyst's machine with no external services.

| Feature | Detail |
|---|---|
| File formats | CSV, XLSX, XLS |
| Variables per axis | Up to 2 row × 2 column variables |
| Cell content | Count (N) and column % displayed in the same cell |
| Statistical tests | χ², Fisher's exact, Mann-Whitney U, Kruskal-Wallis, Spearman ρ, Pearson r |
| Effect sizes | Cramér's V (bias-corrected), rank-biserial r, η², Spearman's ρ, Pearson's r |
| Weighting | Optional — weighted counts/% in table; statistical tests use unweighted data |
| Crosstab table | Shown for categorical combinations; replaced by descriptive stats table for interval × interval |
| Charts | Labels adapt by variable type: Clustered/Stacked bar (categorical); Violin/Box plot (interval × categorical); Scatter plot only (interval × interval) |
| Export | Crosstab or summary table → Excel, CSV, or PNG; charts → PNG |

---

## 2. Installation and Running

**Prerequisites:** Python 3.10+, pip

```bash
cd "path/to/crosstabs"
pip install -r requirements.txt
python main.py
```

**`requirements.txt` notes**
- `openpyxl>=3.0.9,!=3.1.0,!=3.1.1` — versions 3.1.0–3.1.1 broke the `synchVertical` worksheet property. The data loader catches the resulting `TypeError` and shows a helpful pip fix command, but pinning the version prevents it entirely.
- `xlrd>=2.0.1` — required only for `.xls` (legacy Excel). `.xlsx` uses `openpyxl`.

---

## 3. Architecture

```
crosstabs/
├── core/                   ← Pure Python. No PyQt6 imports.
│   ├── data_loader.py
│   ├── variable_classifier.py
│   ├── consolidator.py
│   ├── crosstab_builder.py
│   ├── statistics.py
│   └── exporter.py
│
├── ui/
│   ├── palette.py          ← All color constants + global QSS stylesheet
│   ├── main_window.py      ← Orchestrator; sole bridge between core/ and ui/
│   ├── dialogs/
│   │   └── consolidate_dialog.py
│   └── panels/
│       ├── file_panel.py
│       ├── variable_panel.py
│       ├── crosstab_panel.py
│       ├── stats_panel.py
│       └── chart_panel.py
│
└── main.py                 ← Entry point
```

**Signal flow**
1. `FilePanel` emits `data_loaded(df, path)` → `MainWindow` classifies columns, passes df + types to `VariablePanel`.
2. `VariablePanel` emits `analysis_requested(config)` → `MainWindow` runs the core pipeline and pushes results to the three display panels.

**Core pipeline** (in `MainWindow._on_analysis_requested`):
1. Apply response consolidations via `ResponseConsolidator`
2. Build contingency table via `CrosstabBuilder.build()`
3. Format for display via `CrosstabBuilder.format_display()`
4. Run statistical test via `StatisticalTester.test()`
5. Push results to `CrosstabPanel`, `StatsPanel`, `ChartPanel`

---

## 4. Core Modules

### `core/data_loader.py` — `DataLoader`
Loads CSV or Excel files into a pandas DataFrame.

- `get_sheet_names(path)` — returns sheet list for Excel files; used to populate the sheet selector dialog.
- `load(path, sheet_name=None)` — reads the file. Extension check is case-insensitive (`.XLSX` works). Catches `TypeError` from the openpyxl `synchVertical` bug and re-raises as a `ValueError` with a human-readable fix.

### `core/variable_classifier.py` — `VariableType`, `VariableClassifier`
Automatically assigns each column a measurement level.

`VariableType` enum values: `Nominal`, `Ordinal`, `Interval`

**Classification heuristic** (applied per column):
1. Non-numeric → `Nominal`
2. Numeric, Likert-scale pattern (contiguous integers, starts at 0 or 1, ends between 4–12, ≥3 values) → `Ordinal`
3. Numeric, ≤15 unique values → `Ordinal`
4. Numeric, >50% unique values or >20 distinct values → `Interval`
5. Otherwise → `Ordinal`

The analyst can override the inferred type in the UI.

### `core/consolidator.py` — `ResponseConsolidator`
Groups response categories before building the crosstab.

- `set_from_dict(mappings)` — accepts `{column: {orig_value: group_name}}`. Original value types (int, str, float) are preserved as dict keys so that pandas `.map()` comparisons work correctly.
- `apply(df)` — returns a copy of `df` with consolidations applied. Columns with no mapping are returned unchanged.
- `set_mapping(col, mapping)` / `remove_mapping(col)` — fine-grained updates.

### `core/crosstab_builder.py` — `CrosstabResult`, `DisplayResult`, `CrosstabBuilder`

**`CrosstabResult`** (dataclass) — raw contingency table output:
- `counts` — full table with margins (Total row + Total column)
- `col_pct` — column percentages for data cells only (no margins)
- `n_total` — always unweighted sample size
- `n_weighted` — sum of weights; `None` when no weight column used

**`DisplayResult`** (dataclass) — ready-to-render representation:
- `df` — flat DataFrame. Each category gets one visual row; N is stored as the cell display value and the paired % is stored in a custom `UserRole` for the two-line delegate to paint.
- `pct_row_indices` — retained for compatibility; used by `_populate_table` to pair N and % rows.
- `total_row_index` — row position of the Total row in `df`
- `total_col` — column name for the Total column (`"Total"`)

**`CrosstabBuilder.build()`** supports three modes:
- **Standard** — raw counts + column %
- **Weighted** — cell values are sum of weights; column % from weighted counts
- **Aggfunc** — mean/median/sum/count of a third numeric variable; no % rows

**`CrosstabBuilder.format_display()`** — converts `CrosstabResult.counts` into the flat `DisplayResult.df`. Alternating N/% rows are produced internally; the UI merges them into single visual rows via `_TwoLineCellDelegate`.

### `core/statistics.py` — `StatTestResult`, `StatisticalTester`

See [Section 6](#6-statistical-logic) for the full decision tree.

**`StatTestResult`** (dataclass): `test_name`, `statistic`, `p_value`, `is_significant`, `effect_size_name`, `effect_size`, `effect_size_label`, `notes` (list), `additional` (dict for supplemental tests).

**`StatisticalTester.test(df, row_vars, col_vars, var_types, weighted=False)`** — selects and runs the appropriate test. When `weighted=True`, a note is appended to `result.notes` explaining that the test uses unweighted data.

### `core/exporter.py` — `Exporter`
- `export_table_excel(df, path)` — saves the display DataFrame to `.xlsx` via `openpyxl`.
- `export_table_csv(df, path)` — saves to `.csv`.
- `export_table_png(df, path, dpi=150)` — renders the display DataFrame as a matplotlib table figure and saves to PNG. Figure size scales with row/column count.
- `export_figure(fig, path, dpi=150)` — saves a matplotlib Figure to PNG.

---

## 5. UI Modules

### `ui/palette.py`
Single source of truth for all colors and the global Qt Style Sheet.

Key constants: `PRIMARY`, `GREY_50`–`GREY_900`, `SIG_TRUE`, `SIG_FALSE`, `TABLE_*`, `EFFECT_LABEL_COLORS`, `MPL_PALETTE`, `MPL_SCATTER`, `MPL_TREND`, `APP_STYLESHEET`.

To restyle the application change values in this file — no panel code needs to be touched.

### `ui/main_window.py` — `MainWindow`
Top-level `QMainWindow`. Owns all core objects (`VariableClassifier`, `ResponseConsolidator`, `CrosstabBuilder`, `StatisticalTester`). Connects signals from `FilePanel` and `VariablePanel` and drives the core pipeline.

### `ui/dialogs/consolidate_dialog.py` — `ConsolidateDialog`
Two-column `QTableWidget` showing Original Value (read-only) and New Group Name (editable). The "Set selected rows to:" helper row lets the analyst quickly assign a common name to multiple values. `get_mapping()` returns `{original_value: group_name}` with original Python types preserved as keys.

### `ui/panels/file_panel.py` — `FilePanel`
Browse button → sheet selector for Excel → `DataLoader.load()`. Emits `data_loaded(df, path)` on success. Displays row/column counts after loading.

### `ui/panels/variable_panel.py` — `VariablePanel`, `VariableSelector`
**`VariableSelector`** — one slot: `[variable combo ──────] [type 135px] [Consolidate… 100px]`. The variable combo uses `setMinimumContentsLength(10)` with `AdjustToMinimumContentsLengthWithIcon` to prevent text overflow without making the combo excessively wide.

**`VariablePanel`** — groups in order (top to bottom): Column Variables (X-axis), Row Variables (Y-axis), Aggregation (optional), Survey Weights (optional), Run Analysis button. Each variable group supports a second variable via an "Add 2nd Variable" button.

Emits `analysis_requested(config)` where `config` contains `row_vars`, `col_vars`, `var_types`, `consolidations`, `aggfunc_col`, `aggfunc`, `weight_col`.

### `ui/panels/crosstab_panel.py` — `CrosstabPanel`
Has two display modes set by `MainWindow`:

- **Crosstab mode** (`set_result`) — renders `DisplayResult` as a `QTableWidget`. N and % values for each category are shown in the same cell via `_TwoLineCellDelegate`: the count appears in the top half; the column percentage appears in the bottom half in smaller, dimmed text. Tab label is "Crosstab Table".
- **Summary mode** (`set_summary`) — used when all selected variables are Interval. Renders a plain descriptive statistics table (N, Mean, Median, Std Dev, Min, Max, one row per variable) via `_populate_simple`. Tab label changes to "Summary Statistics".

Color logic: column headers → `TABLE_HEADER_BG` (dark slate). Three export buttons (Excel, CSV, PNG) work in both modes.

### `ui/panels/stats_panel.py` — `StatsPanel`
Renders `StatTestResult` as styled HTML in a read-only `QTextEdit`. Note text is HTML-escaped before insertion to prevent `<` characters (e.g. in "expected cells are < 5") from truncating the display.

Supplemental sections:
- **Spearman's ρ** — shown when both variables are Ordinal (ordinal-association complement to χ²)
- **Supplemental Spearman** — shown when Pearson is used (non-parametric cross-check)

### `ui/panels/chart_panel.py` — `ChartPanel`
Embeds a `FigureCanvasQTAgg` (matplotlib) with a `NavigationToolbar2QT`. Radio button labels and visibility adapt dynamically to the selected variable types:

| Variable combination | Radio button 1 | Radio button 2 |
|---|---|---|
| Both categorical | Clustered bar chart (default) | Stacked bar chart |
| Interval × Categorical | Violin plot (default) | Box plot |
| Both interval | Scatter plot (disabled — no choice) | hidden |

Auto-selected chart logic by variable type:
- Both categorical + Clustered → grouped countplot (`sns.countplot`)
- Both categorical + Stacked → 100% stacked bar (% only; counts are already in the table)
- Interval × Categorical → violin plot or box plot (user toggle)
- Interval × Interval → scatter plot with linear trend line (radio button is informational only)

All charts draw colors from `ui/palette.py`: categorical charts use `MPL_PALETTE` (passed as `palette=` to seaborn or as explicit colors to pandas `.plot()`), scatter points use `MPL_SCATTER`, and the trend line uses `MPL_TREND`. Titles follow the uniform scheme `"{A}  by  {B}"` (scatter uses `"{X}  ×  {Y}"`). Changing those constants in `palette.py` updates every chart type simultaneously.

---

## 6. Statistical Logic

### Test selection

| Row type | Col type | Test | Effect size |
|---|---|---|---|
| Nominal | Nominal | χ² or Fisher's exact | Cramér's V (bias-corrected) |
| Nominal | Ordinal | χ² or Fisher's exact | Cramér's V |
| Ordinal | Ordinal | χ² or Fisher's exact + Spearman's ρ | Cramér's V + Spearman's ρ |
| Interval | Categorical | Mann-Whitney U (2 groups) or Kruskal-Wallis (k > 2) | Rank-biserial r or η² |
| Interval | Interval | Pearson r (both normal) or Spearman ρ | Pearson's r or Spearman's ρ |

### χ² assumption checking
Before every χ²/Fisher test, the expected cell counts are checked:
- If ≥ 80% of expected cells are ≥ 5 and no cell is < 1 → χ² is valid.
- Violated + 2×2 table → Fisher's Exact Test (odds ratio reported).
- Violated + larger table → χ² with a warning note.

Yates' continuity correction is applied automatically for 2×2 χ² tables.

### Bias-corrected Cramér's V
Uses the Bergsma (2013) correction to remove upward bias in small samples. Thresholds follow Lovakov & Agadullina (2021): Small/Medium/Large cutoffs depend on the minimum table dimension.

### Normality testing (Interval × Interval)
- n < 3 → Spearman (insufficient data)
- 3 ≤ n ≤ 5000 → Shapiro-Wilk
- n > 5000 → D'Agostino-Pearson omnibus test

Both variables must pass (p > 0.05) to use Pearson; otherwise Spearman is used.

### Survey weights
Weighted counts and column percentages are shown in the crosstab table for population estimates. Statistical tests always use the unweighted sample because weighted counts violate the independence assumption of χ² and similar tests. A note is shown in the Statistics tab when weights are active.

---

## 7. Customizing Colors

All colors are defined as constants at the top of `ui/palette.py`. Change any value there to update every panel that uses it. The `APP_STYLESHEET` f-string at the bottom of the same file uses those constants to build the global Qt Style Sheet applied at startup in `main.py`.

To change the chart color palette, update `MPL_PALETTE` (seaborn named palette), `MPL_SCATTER`, and `MPL_TREND` in `palette.py`.
