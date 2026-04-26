import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QPushButton, QCheckBox, QFormLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional

from core.variable_classifier import VariableType
from ui.dialogs.consolidate_dialog import ConsolidateDialog


# ── VariableSelector ──────────────────────────────────────────────────────────

class VariableSelector(QWidget):
    """
    One row of controls representing a single variable slot:
        [variable dropdown ─────────] [type] [Consolidate…]

    The type dropdown auto-updates when the variable changes (reflecting the
    classifier's verdict) but can be manually overridden by the analyst.
    """

    consolidate_clicked = pyqtSignal(str)  # emits the column name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._auto_types: dict[str, VariableType] = {}

        self.var_combo = QComboBox()
        self.var_combo.addItem("(none)")
        self.var_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.var_combo.setMinimumContentsLength(10)
        self.var_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        self.type_combo = QComboBox()
        self.type_combo.addItems([vt.value for vt in VariableType])
        self.type_combo.setFixedWidth(135)
        self.type_combo.setEnabled(False)

        self.consolidate_btn = QPushButton("Consolidate…")
        self.consolidate_btn.setFixedWidth(100)
        self.consolidate_btn.setStyleSheet("font-size: 11px;")
        self.consolidate_btn.setEnabled(False)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.var_combo, 1)
        row.addWidget(self.type_combo)
        row.addWidget(self.consolidate_btn)

        self.var_combo.currentTextChanged.connect(self._on_var_changed)
        self.consolidate_btn.clicked.connect(self._on_consolidate)

    def populate(self, columns: list[str], auto_types: dict[str, VariableType]) -> None:
        current = self.var_combo.currentText()
        self.var_combo.blockSignals(True)
        self.var_combo.clear()
        self.var_combo.addItem("(none)")
        self.var_combo.addItems(columns)
        if current in columns:
            self.var_combo.setCurrentText(current)
        self.var_combo.blockSignals(False)
        self._auto_types = auto_types
        self._sync_type()

    def get_variable(self) -> Optional[str]:
        v = self.var_combo.currentText()
        return v if v != "(none)" else None

    def get_type(self) -> Optional[VariableType]:
        if self.get_variable() is None:
            return None
        text = self.type_combo.currentText()
        for vt in VariableType:
            if vt.value == text:
                return vt
        return VariableType.NOMINAL

    def _on_var_changed(self, col: str) -> None:
        active = col != "(none)"
        self.type_combo.setEnabled(active)
        self.consolidate_btn.setEnabled(active)
        self._sync_type()

    def _sync_type(self) -> None:
        col = self.var_combo.currentText()
        if col != "(none)" and col in self._auto_types:
            self.type_combo.blockSignals(True)
            self.type_combo.setCurrentText(self._auto_types[col].value)
            self.type_combo.blockSignals(False)

    def _on_consolidate(self) -> None:
        col = self.get_variable()
        if col:
            self.consolidate_clicked.emit(col)


# ── VariablePanel ─────────────────────────────────────────────────────────────

class VariablePanel(QWidget):
    """
    Lets the analyst choose row / column variables (up to 2 each), override
    inferred variable types, define response consolidations, apply a weight
    variable, and launch the analysis.

    Emits analysis_requested(config) where config is a dict:
        row_vars       : list[str]
        col_vars       : list[str]
        var_types      : dict[str, VariableType]
        consolidations : dict[str, dict]   — {col: {orig_val: group_name}}
        aggfunc_col    : str | None
        aggfunc        : str
        weight_col     : str | None
    """

    analysis_requested = pyqtSignal(object)  # dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._auto_types: dict[str, VariableType] = {}
        self._consolidations: dict[str, dict] = {}
        self._build_ui()

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_data(
        self,
        df: pd.DataFrame,
        auto_types: dict[str, VariableType],
    ) -> None:
        self._df = df
        self._auto_types = auto_types
        self._consolidations.clear()
        columns = df.columns.tolist()
        for sel in self._all_selectors():
            sel.populate(columns, auto_types)

        numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
        self.agg_col_combo.clear()
        self.agg_col_combo.addItems(numeric_cols)
        self.weight_col_combo.clear()
        self.weight_col_combo.addItem("(none)")
        self.weight_col_combo.addItems(numeric_cols)
        self.run_btn.setEnabled(True)

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(self._build_var_group("Column Variables  (X-axis)", "col"))
        layout.addWidget(self._build_var_group("Row Variables  (Y-axis)", "row"))
        layout.addWidget(self._build_agg_group())
        layout.addWidget(self._build_weight_group())

        self.run_btn = QPushButton("▶  Run Analysis")
        self.run_btn.setObjectName("run_btn")   # QSS selector
        self.run_btn.setEnabled(False)
        self.run_btn.setMinimumHeight(40)
        self.run_btn.clicked.connect(self._on_run)
        layout.addWidget(self.run_btn)
        layout.addStretch()

    def _build_var_group(self, title: str, axis: str) -> QGroupBox:
        group = QGroupBox(title)
        g_layout = QVBoxLayout(group)
        g_layout.setSpacing(4)

        sel1 = VariableSelector()
        sel2 = VariableSelector()
        sel2.setVisible(False)
        sel1.consolidate_clicked.connect(self._open_consolidate)
        sel2.consolidate_clicked.connect(self._open_consolidate)

        add_btn    = QPushButton(f"+ Add 2nd {axis.capitalize()} Variable")
        remove_btn = QPushButton(f"− Remove 2nd {axis.capitalize()} Variable")
        remove_btn.setVisible(False)

        g_layout.addWidget(QLabel("Primary:"))
        g_layout.addWidget(sel1)
        g_layout.addWidget(sel2)
        g_layout.addWidget(add_btn)
        g_layout.addWidget(remove_btn)

        def _add():
            sel2.setVisible(True)
            add_btn.setVisible(False)
            remove_btn.setVisible(True)

        def _remove():
            sel2.setVisible(False)
            sel2.var_combo.setCurrentIndex(0)
            add_btn.setVisible(True)
            remove_btn.setVisible(False)

        add_btn.clicked.connect(_add)
        remove_btn.clicked.connect(_remove)

        if axis == "row":
            self.row_sel_1 = sel1
            self.row_sel_2 = sel2
        else:
            self.col_sel_1 = sel1
            self.col_sel_2 = sel2

        return group

    def _build_agg_group(self) -> QGroupBox:
        group = QGroupBox("Aggregation  (optional)")
        g_layout = QVBoxLayout(group)
        g_layout.setSpacing(4)

        self.agg_check = QCheckBox("Aggregate a third variable in each cell")
        g_layout.addWidget(self.agg_check)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self.agg_col_combo  = QComboBox()
        self.agg_func_combo = QComboBox()
        self.agg_func_combo.addItems(["mean", "median", "sum", "count"])
        self.agg_col_combo.setEnabled(False)
        self.agg_func_combo.setEnabled(False)
        form.addRow("Variable:", self.agg_col_combo)
        form.addRow("Function:", self.agg_func_combo)
        g_layout.addLayout(form)

        self.agg_check.toggled.connect(self.agg_col_combo.setEnabled)
        self.agg_check.toggled.connect(self.agg_func_combo.setEnabled)
        return group

    def _build_weight_group(self) -> QGroupBox:
        group = QGroupBox("Survey Weights  (optional)")
        g_layout = QVBoxLayout(group)
        g_layout.setSpacing(4)

        self.weight_check = QCheckBox("Apply weighting")
        g_layout.addWidget(self.weight_check)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self.weight_col_combo = QComboBox()
        self.weight_col_combo.setEnabled(False)
        form.addRow("Weight variable:", self.weight_col_combo)
        g_layout.addLayout(form)

        note = QLabel(
            "Weighted counts and column % are shown in the table.\n"
            "Statistical tests use unweighted data for valid inference."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px;")
        g_layout.addWidget(note)

        self.weight_check.toggled.connect(self.weight_col_combo.setEnabled)
        return group

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _all_selectors(self) -> list[VariableSelector]:
        return [self.row_sel_1, self.row_sel_2, self.col_sel_1, self.col_sel_2]

    def _open_consolidate(self, col: str) -> None:
        if self._df is None:
            return
        values = self._df[col].dropna().unique().tolist()
        existing = self._consolidations.get(col)
        dlg = ConsolidateDialog(col, values, existing_mapping=existing, parent=self)
        if dlg.exec():
            mapping = dlg.get_mapping()
            if any(str(orig) != grp for orig, grp in mapping.items()):
                self._consolidations[col] = mapping
            else:
                self._consolidations.pop(col, None)

    def _on_run(self) -> None:
        row_vars = [v for v in [
            self.row_sel_1.get_variable(),
            self.row_sel_2.get_variable(),
        ] if v]
        col_vars = [v for v in [
            self.col_sel_1.get_variable(),
            self.col_sel_2.get_variable(),
        ] if v]

        if not row_vars:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Missing selection",
                                "Please select at least one row variable.")
            return
        if not col_vars:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Missing selection",
                                "Please select at least one column variable.")
            return

        var_types: dict[str, VariableType] = {}
        for sel in self._all_selectors():
            v = sel.get_variable()
            t = sel.get_type()
            if v and t:
                var_types[v] = t

        weight_col = None
        if self.weight_check.isChecked():
            w = self.weight_col_combo.currentText()
            if w and w != "(none)":
                weight_col = w

        config = {
            "row_vars":       row_vars,
            "col_vars":       col_vars,
            "var_types":      var_types,
            "consolidations": dict(self._consolidations),
            "aggfunc_col":    self.agg_col_combo.currentText() if self.agg_check.isChecked() else None,
            "aggfunc":        self.agg_func_combo.currentText(),
            "weight_col":     weight_col,
        }
        self.analysis_requested.emit(config)
