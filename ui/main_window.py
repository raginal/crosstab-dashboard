import pandas as pd
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter, QScrollArea,
    QTabWidget, QVBoxLayout, QStatusBar, QLabel,
)
from PyQt6.QtCore import Qt

from core.variable_classifier import VariableClassifier
from core.consolidator import ResponseConsolidator
from core.crosstab_builder import CrosstabBuilder
from core.statistics import StatisticalTester
from core.exporter import Exporter

from ui.panels.file_panel import FilePanel
from ui.panels.variable_panel import VariablePanel
from ui.panels.crosstab_panel import CrosstabPanel
from ui.panels.stats_panel import StatsPanel
from ui.panels.chart_panel import ChartPanel


class MainWindow(QMainWindow):
    """
    Top-level window and analysis orchestrator.

    Signal flow
    ───────────
    1. FilePanel  emits  data_loaded(df, path)
         → MainWindow classifies columns, passes df + types to VariablePanel.
    2. VariablePanel  emits  analysis_requested(config)
         → MainWindow runs the full core pipeline and pushes results to the
           three display panels.

    The core pipeline (on_analysis_requested):
        a. Apply response consolidations (ResponseConsolidator)
        b. Build contingency table (CrosstabBuilder)
        c. Format for display (CrosstabBuilder.format_display)
        d. Run statistical test (StatisticalTester)
        e. Push to CrosstabPanel, StatsPanel, ChartPanel
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Survey Crosstab Analyzer")
        self.setMinimumSize(1200, 720)

        self._df: pd.DataFrame | None = None
        self._classifier  = VariableClassifier()
        self._consolidator = ResponseConsolidator()
        self._builder     = CrosstabBuilder()
        self._tester      = StatisticalTester()

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left panel (controls) ─────────────────────────────────────────────
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)

        self.file_panel = FilePanel()
        self.var_panel  = VariablePanel()

        left_layout.addWidget(self.file_panel)
        left_layout.addWidget(self.var_panel)
        left_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(left_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(380)
        scroll.setMaximumWidth(460)

        # ── Right panel (results tabs) ────────────────────────────────────────
        self.right_tabs = QTabWidget()

        self.crosstab_panel = CrosstabPanel()
        self.stats_panel    = StatsPanel()
        self.chart_panel    = ChartPanel()

        self.right_tabs.addTab(self.crosstab_panel, "Crosstab Table")
        self.right_tabs.addTab(self.stats_panel,    "Statistical Results")
        self.right_tabs.addTab(self.chart_panel,    "Charts")

        splitter.addWidget(scroll)
        splitter.addWidget(self.right_tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Load a data file to begin.")

        # Signals
        self.file_panel.data_loaded.connect(self._on_data_loaded)
        self.var_panel.analysis_requested.connect(self._on_analysis_requested)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_data_loaded(self, df: pd.DataFrame, path: str) -> None:
        self._df = df
        auto_types = self._classifier.classify_all(df)
        self.var_panel.set_data(df, auto_types)
        self.crosstab_panel.clear()
        self.stats_panel.clear()
        self.chart_panel.clear()
        n_rows, n_cols = df.shape
        self._status.showMessage(
            f"Loaded: {path}  |  {n_rows:,} rows  ×  {n_cols} columns  "
            f"— select variables and click Run Analysis"
        )

    def _on_analysis_requested(self, config: dict) -> None:
        if self._df is None:
            return

        try:
            # Step 1 — apply consolidations
            self._consolidator.set_from_dict(config["consolidations"])
            df_work = self._consolidator.apply(self._df)

            # Step 2 — build crosstab
            result = self._builder.build(
                df_work,
                row_vars=config["row_vars"],
                col_vars=config["col_vars"],
                aggfunc_col=config.get("aggfunc_col"),
                aggfunc=config.get("aggfunc", "mean"),
                weight_col=config.get("weight_col"),
            )

            # Step 3 — format display
            display = self._builder.format_display(result)

            # Step 4 — run stats (skip for aggfunc mode)
            stat_result = None
            if not result.aggfunc_col:
                stat_result = self._tester.test(
                    df_work,
                    row_vars=config["row_vars"],
                    col_vars=config["col_vars"],
                    var_types=config["var_types"],
                    weighted=bool(config.get("weight_col")),
                )

            # Step 5 — push to panels
            self.crosstab_panel.set_result(display, result, stat_result)
            if stat_result:
                self.stats_panel.set_result(stat_result, result.n_total)
            else:
                self.stats_panel.clear()

            self.chart_panel.set_data(
                df_work,
                row_vars=config["row_vars"],
                col_vars=config["col_vars"],
                var_types=config["var_types"],
            )

            # Switch to crosstab tab and report
            self.right_tabs.setCurrentIndex(0)
            sig_msg = ""
            if stat_result:
                sig_msg = (
                    f"  |  {stat_result.test_name}: "
                    f"p = {stat_result.p_value:.4f} {stat_result.sig_stars}"
                )
            self._status.showMessage(
                f"Analysis complete  |  n = {result.n_total:,}{sig_msg}"
            )

        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Analysis error", str(exc))
            self._status.showMessage("Analysis failed — see error dialog.")
