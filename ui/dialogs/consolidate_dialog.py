from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QAbstractItemView,
    QLineEdit, QHeaderView, QCheckBox, QWidget, QFrame,
)
from PyQt6.QtCore import Qt
from typing import Optional

from ui.palette import GREY_200


class ConsolidateDialog(QDialog):
    """
    Lets the analyst filter and recode response options.

    Three-column table: Include (checkbox) | Original Value | New Group Name.
    Unchecked rows are excluded from the analysis entirely.
    Values sharing the same group name are merged in the analysis.

    Original value types (int, float, str, …) are preserved in the returned
    mapping so that pandas .map() comparisons work correctly.
    Filtered values map to None in the returned dict.
    """

    def __init__(
        self,
        column: str,
        values: list,
        existing_mapping: Optional[dict] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Clean responses — {column}")
        self.setMinimumSize(520, 420)
        self.resize(580, 500)

        self._orig_values: list = sorted(values, key=lambda x: str(x))
        self._checkboxes: list[QCheckBox] = []

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        instr = QLabel(
            "Edit <b>New Group Name</b> to merge values together. "
            "Rows sharing the same group name will be combined in the crosstab. "
            "Uncheck <b>Include</b> to exclude a value from the analysis entirely."
        )
        instr.setWordWrap(True)
        layout.addWidget(instr)

        # ── Table ─────────────────────────────────────────────────────────
        self.table = QTableWidget(len(self._orig_values), 3)
        self.table.setHorizontalHeaderLabels(["Include", "Original Value", "New Group Name"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 62)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.cellClicked.connect(self._on_cell_clicked)

        for i, val in enumerate(self._orig_values):
            # Include column: centered QCheckBox in a transparent container
            is_included = True
            if existing_mapping is not None:
                is_included = existing_mapping.get(val) is not None
            cb = QCheckBox()
            cb.setChecked(is_included)
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            cb_layout = QHBoxLayout(container)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.addWidget(cb)
            self.table.setCellWidget(i, 0, container)
            self._checkboxes.append(cb)

            # Original value — read-only
            orig_item = QTableWidgetItem(str(val))
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 1, orig_item)

            # Group name — editable; pre-fill from existing mapping or identity
            if existing_mapping is not None and existing_mapping.get(val) is not None:
                group = str(existing_mapping[val])
            else:
                group = str(val)
            self.table.setItem(i, 2, QTableWidgetItem(group))

        layout.addWidget(self.table)

        # ── Controls row (filter section | consolidation section) ─────────
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(0)

        # — Filter section —
        all_checked = all(
            existing_mapping.get(v) is not None for v in self._orig_values
        ) if existing_mapping is not None else True
        self._all_selected = all_checked
        self._toggle_btn = QPushButton("Unselect all" if all_checked else "Select all")
        self._toggle_btn.setFixedWidth(100)
        self._toggle_btn.clicked.connect(self._toggle_select_all)
        ctrl_layout.addWidget(self._toggle_btn)

        # Vertical divider
        ctrl_layout.addSpacing(10)
        sep_v = QFrame()
        sep_v.setFrameShape(QFrame.Shape.VLine)
        sep_v.setFrameShadow(QFrame.Shadow.Plain)
        sep_v.setStyleSheet(f"color: {GREY_200};")
        ctrl_layout.addWidget(sep_v)
        ctrl_layout.addSpacing(10)

        # — Consolidation section —
        ctrl_layout.addWidget(QLabel("Set selected rows to:"))
        ctrl_layout.addSpacing(6)
        self._quick_edit = QLineEdit()
        self._quick_edit.setPlaceholderText("group name …")
        apply_btn = QPushButton("Apply to selection")
        apply_btn.clicked.connect(self._apply_quick_group)
        reset_btn = QPushButton("Reset to original")
        reset_btn.clicked.connect(self._reset)
        ctrl_layout.addWidget(self._quick_edit, 1)
        ctrl_layout.addSpacing(6)
        ctrl_layout.addWidget(apply_btn)
        ctrl_layout.addSpacing(4)
        ctrl_layout.addWidget(reset_btn)

        layout.addLayout(ctrl_layout)

        # ── Horizontal divider ────────────────────────────────────────────
        sep_h = QFrame()
        sep_h.setFrameShape(QFrame.Shape.HLine)
        sep_h.setFrameShadow(QFrame.Shadow.Plain)
        sep_h.setStyleSheet(f"color: {GREY_200};")
        layout.addWidget(sep_h)

        # ── Close button ──────────────────────────────────────────────────
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        # Clicking the Original Value column toggles the Include checkbox for that row
        if col == 1:
            cb = self._checkboxes[row]
            cb.setChecked(not cb.isChecked())

    def _toggle_select_all(self) -> None:
        self._all_selected = not self._all_selected
        for cb in self._checkboxes:
            cb.setChecked(self._all_selected)
        self._toggle_btn.setText("Unselect all" if self._all_selected else "Select all")

    def _reset(self) -> None:
        for i, val in enumerate(self._orig_values):
            self._checkboxes[i].setChecked(True)
            self.table.item(i, 2).setText(str(val))
        self._all_selected = True
        self._toggle_btn.setText("Unselect all")

    def _apply_quick_group(self) -> None:
        group_name = self._quick_edit.text().strip()
        if not group_name:
            return
        for item in self.table.selectedItems():
            if item.column() == 2:
                item.setText(group_name)

    def get_mapping(self) -> dict:
        """
        Return {original_value: group_name_str} for included rows,
        {original_value: None} for filtered-out rows.
        """
        result = {}
        for i, val in enumerate(self._orig_values):
            if self._checkboxes[i].isChecked():
                result[val] = self.table.item(i, 2).text().strip() or str(val)
            else:
                result[val] = None
        return result
