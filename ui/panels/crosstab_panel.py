import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QFileDialog, QMessageBox, QHeaderView,
    QSizePolicy, QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QFont, QColor, QBrush

from core.crosstab_builder import CrosstabResult, DisplayResult
from core.exporter import Exporter
from core.statistics import StatTestResult
from ui.palette import (
    TABLE_PCT_BG, TABLE_PCT_FG,
    TABLE_TOTAL_BG, TABLE_HEADER_BG, TABLE_HEADER_FG,
    GREY_200,
)

_PCT_ROLE = Qt.ItemDataRole.UserRole + 1


class _TwoLineCellDelegate(QStyledItemDelegate):
    """Paints N value on the top half and % value (dimmed) on the bottom half."""

    def paint(self, painter, option, index):
        pct = index.data(_PCT_ROLE)
        if pct is None:
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        w = opt.widget
        w.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, w)

        painter.save()
        r = option.rect
        mid_y = r.top() + r.height() // 2
        n_text = index.data(Qt.ItemDataRole.DisplayRole) or ""

        fg = index.data(Qt.ItemDataRole.ForegroundRole)
        n_color = fg.color() if fg else QColor("#334155")

        top_r = QRect(r.left() + 2, r.top() + 1, r.width() - 4, mid_y - r.top() - 2)
        painter.setPen(n_color)
        painter.drawText(top_r, Qt.AlignmentFlag.AlignCenter, n_text)

        btm_r = QRect(r.left() + 2, mid_y + 1, r.width() - 4, r.bottom() - mid_y - 2)
        pct_font = QFont(painter.font())
        pct_font.setPointSize(max(8, painter.font().pointSize() - 1))
        painter.setFont(pct_font)
        painter.setPen(QColor(TABLE_PCT_FG))
        painter.drawText(btm_r, Qt.AlignmentFlag.AlignCenter, pct)
        painter.restore()

    def sizeHint(self, option, index):
        sh = super().sizeHint(option, index)
        if index.data(_PCT_ROLE) is not None:
            return QSize(sh.width(), max(44, sh.height()))
        return sh


class CrosstabPanel(QWidget):
    """
    Renders the contingency table as a QTableWidget.

    Layout per logical row:
        <RowValue>  N   |  count  count  …  total_count
        <RowValue>  %   |  x.x%   x.x%  …   (blank)
        Total       N   |  total  total  …  grand_total

    Styling:
        N rows     → white
        % rows     → light-grey background, dimmed text
        Total row  → light-blue background, bold
        Total col  → bold, light-blue background

    Statistical significance is shown only in the caption line below the
    table (not as asterisks inside cells — the Statistics tab has full
    detail on the test results).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._exporter = Exporter()
        self._display: DisplayResult | None = None
        self._result: CrosstabResult | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.table)

        self.caption = QLabel("")
        self.caption.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        layout.addWidget(self.caption)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.export_excel_btn = QPushButton("Export to Excel")
        self.export_csv_btn   = QPushButton("Export to CSV")
        self.export_excel_btn.setEnabled(False)
        self.export_csv_btn.setEnabled(False)
        self.export_excel_btn.clicked.connect(self._export_excel)
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_row.addWidget(self.export_excel_btn)
        btn_row.addWidget(self.export_csv_btn)
        layout.addLayout(btn_row)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_result(
        self,
        display: DisplayResult,
        result: CrosstabResult,
        stat_result: StatTestResult | None = None,
    ) -> None:
        self._display = display
        self._result  = result
        self._populate_table(display)
        self._update_caption(result, stat_result)
        self.export_excel_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)

    def clear(self) -> None:
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.caption.setText("")
        self.export_excel_btn.setEnabled(False)
        self.export_csv_btn.setEnabled(False)

    # ── Private ────────────────────────────────────────────────────────────────

    def _populate_table(self, display: DisplayResult) -> None:
        df = display.df
        pct_set = set(display.pct_row_indices)

        # Pair each N-row index with its adjacent %-row index (or None for Total)
        logical_rows: list[tuple[int, int | None]] = []
        i = 0
        while i < len(df):
            if i in pct_set:
                i += 1
                continue
            pct_idx = i + 1 if (i + 1 < len(df) and i + 1 in pct_set) else None
            logical_rows.append((i, pct_idx))
            i += 2 if pct_idx is not None else 1

        n_logical = len(logical_rows)
        n_cols = df.shape[1]

        self.table.clear()
        self.table.setRowCount(n_logical)
        self.table.setColumnCount(n_cols)
        self.table.setHorizontalHeaderLabels(df.columns.tolist())

        # Vertical labels: strip "  N" suffix so each row shows the category name
        vlabels = []
        for n_idx, _ in logical_rows:
            lbl = str(df.index[n_idx])
            if lbl.endswith("  N"):
                lbl = lbl[:-3]
            vlabels.append(lbl)
        self.table.setVerticalHeaderLabels(vlabels)

        self.table.setItemDelegate(_TwoLineCellDelegate(self.table))

        bold = QFont()
        bold.setBold(True)
        clr_total_bg = QColor(TABLE_TOTAL_BG)
        total_cols = {j for j, c in enumerate(df.columns) if c == display.total_col}

        for vis_row, (n_idx, pct_idx) in enumerate(logical_rows):
            is_total = n_idx == display.total_row_index

            for j in range(n_cols):
                raw_n = df.iloc[n_idx, j]
                if pd.isna(raw_n) or raw_n == "":
                    n_text = ""
                elif isinstance(raw_n, (int, np.integer)):
                    n_text = str(int(raw_n))
                elif isinstance(raw_n, float) and raw_n == int(raw_n):
                    n_text = str(int(raw_n))
                else:
                    n_text = str(raw_n)

                item = QTableWidgetItem(n_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if pct_idx is not None:
                    raw_pct = df.iloc[pct_idx, j]
                    pct_text = "" if (pd.isna(raw_pct) or raw_pct == "") else str(raw_pct)
                    item.setData(_PCT_ROLE, pct_text)

                if is_total or j in total_cols:
                    item.setBackground(QBrush(clr_total_bg))
                    item.setFont(bold)

                self.table.setItem(vis_row, j, item)

        hdr_bg = QColor(TABLE_HEADER_BG)
        hdr_fg = QColor(TABLE_HEADER_FG)
        for j in range(n_cols):
            h = self.table.horizontalHeaderItem(j)
            if h:
                h.setBackground(QBrush(hdr_bg))
                h.setForeground(QBrush(hdr_fg))
                h.setFont(bold)

        for vis_row, (n_idx, _) in enumerate(logical_rows):
            if n_idx == display.total_row_index:
                v = self.table.verticalHeaderItem(vis_row)
                if v:
                    v.setFont(bold)

    def _update_caption(
        self, result: CrosstabResult, stat_result: StatTestResult | None
    ) -> None:
        parts = [f"n = {result.n_total:,}"]
        if result.n_weighted is not None:
            parts.append(f"weighted n = {result.n_weighted:,.1f}")
        parts.append(f"Row: {', '.join(result.row_vars)}")
        parts.append(f"Col: {', '.join(result.col_vars)}")
        if stat_result and not np.isnan(stat_result.p_value):
            sig_label = "significant" if stat_result.is_significant else "not significant"
            parts.append(f"p = {stat_result.p_value:.4f} ({sig_label}) — see Statistics tab")
        self.caption.setText("  |  ".join(parts))

    def _export_excel(self) -> None:
        if not self._display:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to Excel", "crosstab.xlsx", "Excel (*.xlsx)"
        )
        if path:
            try:
                self._exporter.export_table_excel(self._display.df, path)
                QMessageBox.information(self, "Export", f"Saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export error", str(e))

    def _export_csv(self) -> None:
        if not self._display:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "crosstab.csv", "CSV (*.csv)"
        )
        if path:
            try:
                self._exporter.export_table_csv(self._display.df, path)
                QMessageBox.information(self, "Export", f"Saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export error", str(e))
