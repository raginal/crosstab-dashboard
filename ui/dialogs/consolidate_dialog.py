from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QDialogButtonBox, QAbstractItemView,
    QLineEdit, QHeaderView,
)
from PyQt6.QtCore import Qt
from typing import Optional


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
        self.resize(560, 480)

        self._orig_values: list = sorted(values, key=lambda x: str(x))

        layout = QVBoxLayout(self)

        instr = QLabel(
            "Edit <b>New Group Name</b> to merge values together. "
            "Rows sharing the same group name will be combined in the crosstab. "
            "Uncheck <b>Include</b> to exclude a value from the analysis entirely."
        )
        instr.setWordWrap(True)
        layout.addWidget(instr)

        self.table = QTableWidget(len(self._orig_values), 3)
        self.table.setHorizontalHeaderLabels(["Include", "Original Value", "New Group Name"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 62)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        for i, val in enumerate(self._orig_values):
            # Include checkbox column
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            is_included = True
            if existing_mapping is not None:
                is_included = existing_mapping.get(val) is not None
            check_item.setCheckState(
                Qt.CheckState.Checked if is_included else Qt.CheckState.Unchecked
            )
            check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, check_item)

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

        # Controls row: toggle-all button + quick-group helper
        ctrl_layout = QHBoxLayout()

        all_checked = all(
            existing_mapping.get(v) is not None for v in self._orig_values
        ) if existing_mapping is not None else True
        self._all_selected = all_checked
        self._toggle_btn = QPushButton("Unselect all" if all_checked else "Select all")
        self._toggle_btn.setFixedWidth(100)
        self._toggle_btn.clicked.connect(self._toggle_select_all)
        ctrl_layout.addWidget(self._toggle_btn)

        ctrl_layout.addSpacing(12)
        ctrl_layout.addWidget(QLabel("Set selected rows to:"))
        self._quick_edit = QLineEdit()
        self._quick_edit.setPlaceholderText("group name …")
        quick_btn = QPushButton("Apply to selection")
        quick_btn.clicked.connect(self._apply_quick_group)
        ctrl_layout.addWidget(self._quick_edit, 1)
        ctrl_layout.addWidget(quick_btn)
        layout.addLayout(ctrl_layout)

        # OK / Cancel / Reset
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        reset_btn = QPushButton("Reset to original")
        btn_box.addButton(reset_btn, QDialogButtonBox.ButtonRole.ResetRole)
        reset_btn.clicked.connect(self._reset)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _toggle_select_all(self) -> None:
        self._all_selected = not self._all_selected
        state = Qt.CheckState.Checked if self._all_selected else Qt.CheckState.Unchecked
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(state)
        self._toggle_btn.setText("Unselect all" if self._all_selected else "Select all")

    def _reset(self) -> None:
        for i, val in enumerate(self._orig_values):
            self.table.item(i, 0).setCheckState(Qt.CheckState.Checked)
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
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked:
                result[val] = self.table.item(i, 2).text().strip() or str(val)
            else:
                result[val] = None
        return result
