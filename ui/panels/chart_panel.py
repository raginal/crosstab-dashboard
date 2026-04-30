import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QButtonGroup, QRadioButton,
)
from PyQt6.QtCore import Qt

from core.variable_classifier import VariableType
from core.exporter import Exporter
from ui.palette import MPL_PALETTE, MPL_SCATTER, MPL_TREND


sns.set_theme(style="whitegrid")


class ChartPanel(QWidget):
    """
    Embeds a matplotlib figure inside PyQt6 and automatically selects the
    chart type based on the variable types of the selected row and column
    variables.

    Chart selection logic:
        Both categorical (Nominal or Ordinal)
            → 100 % stacked bar chart (column distribution by row category)
              + count bar chart side by side
        One Interval, one Categorical
            → Box plot  or  Violin plot  (toggle available)
        Ordinal × Ordinal
            → Box / violin with ordinal codes on Y-axis
        Interval × Interval
            → Scatter plot with Spearman trend line

    For multi-variable selections (2 row or 2 col vars), the primary (first)
    variable is used for the main chart.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._exporter = Exporter()
        self._chart_mode = "violin"  # "violin" | "bar"
        self._current_fig: Figure | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Toolbar row
        ctrl_row = QHBoxLayout()

        self.violin_radio = QRadioButton("Clustered bar chart")
        self.bar_radio    = QRadioButton("Stacked bar chart")
        self.violin_radio.setChecked(True)
        self._last_rt = None
        self._last_ct = None

        mode_group = QButtonGroup(self)
        for rb in (self.violin_radio, self.bar_radio):
            mode_group.addButton(rb)
            ctrl_row.addWidget(rb)

        ctrl_row.addStretch()

        self.export_btn = QPushButton("Export PNG")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._export_png)
        ctrl_row.addWidget(self.export_btn)

        layout.addLayout(ctrl_row)

        # Matplotlib canvas
        self.fig = Figure(figsize=(8, 5), dpi=150, tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.placeholder = QLabel(
            "Run an analysis to see charts here.",
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self.placeholder.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(self.placeholder)

        # Connect radio buttons
        for rb in (self.violin_radio, self.bar_radio):
            rb.toggled.connect(self._on_mode_changed)

        # Initially show placeholder only
        self.canvas.setVisible(False)
        self.toolbar.setVisible(False)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_data(
        self,
        df: pd.DataFrame,
        row_vars: list[str],
        col_vars: list[str],
        var_types: dict[str, VariableType],
    ) -> None:
        self._df = df
        self._row_vars = row_vars
        self._col_vars = col_vars
        self._var_types = var_types
        self._render()

    def clear(self) -> None:
        self.fig.clear()
        self.canvas.draw()
        self.canvas.setVisible(False)
        self.toolbar.setVisible(False)
        self.placeholder.setVisible(True)
        self.export_btn.setEnabled(False)

    # ── Private ────────────────────────────────────────────────────────────────

    def _on_mode_changed(self, checked: bool) -> None:
        if not checked:
            return
        self._chart_mode = "violin" if self.violin_radio.isChecked() else "bar"
        if hasattr(self, "_df"):
            self._render()

    def _update_controls(self, rt: VariableType, ct: VariableType) -> None:
        """Relabel and show/hide radio buttons to match the active variable combination."""
        if rt == self._last_rt and ct == self._last_ct:
            return
        self._last_rt, self._last_ct = rt, ct

        both_interval = (rt == VariableType.INTERVAL and ct == VariableType.INTERVAL)
        both_cat = (
            rt in (VariableType.NOMINAL, VariableType.ORDINAL) and
            ct in (VariableType.NOMINAL, VariableType.ORDINAL)
        )

        for rb in (self.violin_radio, self.bar_radio):
            rb.blockSignals(True)

        if both_interval:
            self.violin_radio.setText("Scatter plot")
            self.violin_radio.setChecked(True)
            self.violin_radio.setEnabled(False)
            self.bar_radio.setVisible(False)
        elif both_cat:
            self.violin_radio.setText("Clustered bar chart")
            self.bar_radio.setText("Stacked bar chart")
            self.violin_radio.setEnabled(True)
            self.bar_radio.setVisible(True)
        else:  # one interval, one categorical
            self.violin_radio.setText("Violin plot")
            self.bar_radio.setText("Box plot")
            self.violin_radio.setEnabled(True)
            self.bar_radio.setVisible(True)

        for rb in (self.violin_radio, self.bar_radio):
            rb.blockSignals(False)

    def _render(self) -> None:
        if not hasattr(self, "_df"):
            return
        self.fig.clear()
        try:
            row0 = self._row_vars[0]
            col0 = self._col_vars[0]
            rt = self._var_types.get(row0, VariableType.NOMINAL)
            ct = self._var_types.get(col0, VariableType.NOMINAL)
            self._update_controls(rt, ct)

            both_cat = (
                rt in (VariableType.NOMINAL, VariableType.ORDINAL) and
                ct in (VariableType.NOMINAL, VariableType.ORDINAL)
            )
            both_interval = (rt == VariableType.INTERVAL and ct == VariableType.INTERVAL)

            if both_interval:
                self._scatter_chart(row0, col0)
            elif both_cat and self._chart_mode == "bar":
                self._stacked_bar_chart(row0, col0)
            elif both_cat:
                self._bar_with_dist(row0, col0)
            elif rt == VariableType.INTERVAL:
                self._dist_chart(col0, row0)   # cat on x, interval on y
            elif ct == VariableType.INTERVAL:
                self._dist_chart(row0, col0)   # cat on x, interval on y
            else:
                # Ordinal × Ordinal: encode one as numeric for y-axis
                self._ordinal_dist_chart(row0, col0)

            self.canvas.draw()
            self.canvas.setVisible(True)
            self.toolbar.setVisible(True)
            self.placeholder.setVisible(False)
            self.export_btn.setEnabled(True)
            self._current_fig = self.fig

        except Exception as exc:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Cannot render chart:\n{exc}",
                    ha='center', va='center', transform=ax.transAxes,
                    color='#b00000', fontsize=11)
            self.canvas.draw()
            self.canvas.setVisible(True)
            self.toolbar.setVisible(True)
            self.placeholder.setVisible(False)

    # ── Chart drawing helpers ──────────────────────────────────────────────────

    def _stacked_bar_chart(self, row_var: str, col_var: str) -> None:
        """100 % stacked bar chart for two categorical variables."""
        df = self._df[[row_var, col_var]].dropna()
        ct = pd.crosstab(df[row_var], df[col_var])
        ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100

        colors = sns.color_palette(MPL_PALETTE, n_colors=len(ct_pct.columns))
        ax = self.fig.add_subplot(111)
        ct_pct.plot(kind='bar', stacked=True, ax=ax, legend=True, color=colors)
        ax.set_title(f"% {col_var}  by  {row_var}")
        ax.set_xlabel(row_var)
        ax.set_ylabel("Column %")
        ax.tick_params(axis='x', rotation=30)
        ax.legend(title=col_var, bbox_to_anchor=(1, 1))

    def _bar_with_dist(self, row_var: str, col_var: str) -> None:
        """Grouped count bar chart for categorical data (when box/violin selected)."""
        df = self._df[[row_var, col_var]].dropna()
        ax = self.fig.add_subplot(111)
        sns.countplot(data=df, x=col_var, hue=row_var, ax=ax, palette=MPL_PALETTE)
        ax.set_title(f"{col_var}  by  {row_var}")
        ax.set_xlabel(col_var)
        ax.set_ylabel("Count")
        ax.tick_params(axis='x', rotation=30)
        ax.legend(title=row_var, bbox_to_anchor=(1, 1))

    def _dist_chart(self, cat_var: str, num_var: str) -> None:
        """Box or violin plot for interval variable across categorical groups."""
        df = self._df[[cat_var, num_var]].dropna()
        ax = self.fig.add_subplot(111)

        order = sorted(df[cat_var].unique(), key=str)
        if self._chart_mode == "violin" and df[cat_var].nunique() > 1:
            try:
                sns.violinplot(data=df, x=cat_var, y=num_var, ax=ax, order=order,
                               inner="box", palette=MPL_PALETTE)
            except Exception:
                sns.boxplot(data=df, x=cat_var, y=num_var, ax=ax, order=order,
                            palette=MPL_PALETTE)
        else:
            sns.boxplot(data=df, x=cat_var, y=num_var, ax=ax, order=order,
                        palette=MPL_PALETTE)

        ax.set_title(f"{num_var}  by  {cat_var}")
        ax.set_xlabel(cat_var)
        ax.set_ylabel(num_var)
        ax.tick_params(axis='x', rotation=30)

        # Add individual group medians as annotation
        for tick, grp in enumerate(order):
            vals = df.loc[df[cat_var] == grp, num_var].dropna()
            if len(vals):
                ax.text(tick, vals.median(), f"  Md={vals.median():.1f}",
                        va='bottom', fontsize=8, color='#444')

    def _ordinal_dist_chart(self, row_var: str, col_var: str) -> None:
        """Box/violin for ordinal × ordinal by encoding row_var as integers."""
        df = self._df[[row_var, col_var]].dropna().copy()
        cats = sorted(df[row_var].unique(), key=str)
        df["_code"] = pd.Categorical(df[row_var], categories=cats).codes.astype(float)

        ax = self.fig.add_subplot(111)
        order = sorted(df[col_var].unique(), key=str)

        if self._chart_mode == "violin" and df[col_var].nunique() > 1:
            try:
                sns.violinplot(data=df, x=col_var, y="_code", ax=ax, order=order,
                               inner="box", palette=MPL_PALETTE)
            except Exception:
                sns.boxplot(data=df, x=col_var, y="_code", ax=ax, order=order,
                            palette=MPL_PALETTE)
        else:
            sns.boxplot(data=df, x=col_var, y="_code", ax=ax, order=order,
                        palette=MPL_PALETTE)

        ax.set_yticks(range(len(cats)))
        ax.set_yticklabels(cats)
        ax.set_title(f"{row_var}  by  {col_var}")
        ax.set_xlabel(col_var)
        ax.set_ylabel(row_var)
        ax.tick_params(axis='x', rotation=30)

    def _scatter_chart(self, x_var: str, y_var: str) -> None:
        """Scatter plot with Spearman regression trend for interval × interval."""
        df = self._df[[x_var, y_var]].dropna()
        ax = self.fig.add_subplot(111)
        ax.scatter(df[x_var], df[y_var], alpha=0.4, s=20, color=MPL_SCATTER)

        # Trend line via numpy polyfit
        if len(df) >= 3:
            m, b = np.polyfit(df[x_var], df[y_var], 1)
            xs = np.linspace(df[x_var].min(), df[x_var].max(), 200)
            ax.plot(xs, m * xs + b, color=MPL_TREND, linewidth=1.5, label="Linear trend")
            ax.legend()

        ax.set_xlabel(x_var)
        ax.set_ylabel(y_var)
        ax.set_title(f"{x_var}  ×  {y_var}")

    # ── Export ─────────────────────────────────────────────────────────────────

    def _export_png(self) -> None:
        if not self._current_fig:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export chart", "chart.png", "PNG image (*.png)"
        )
        if path:
            try:
                self._exporter.export_figure(self._current_fig, path)
                QMessageBox.information(self, "Export", f"Saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export error", str(e))
