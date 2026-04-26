from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QDialogButtonBox, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from typing import Optional


class ConsolidateDialog(QDialog):
    """
    Lets the analyst recode response options into groups.

    Shows a two-column table: Original Value | New Group Name.
    The Original Value column is read-only; the analyst edits New Group Name.
    Values assigned the same group name are merged in the analysis.

    Original value types (int, float, str, …) are preserved in the returned
    mapping so that pandas .map() comparisons work correctly.
    """

    def __init__(
        self,
        column: str,
        values: list,
        existing_mapping: Optional[dict] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Consolidate responses — {column}")
        self.setMinimumSize(480, 420)
        self.resize(520, 480)

        # Store originals with their real type so the returned mapping has correct keys
        self._orig_values: list = sorted(values, key=lambda x: str(x))

        layout = QVBoxLayout(self)

        instr = QLabel(
            "Edit <b>New Group Name</b> to merge values together. "
            "Rows sharing the same group name will be combined in the crosstab."
        )
        instr.setWordWrap(True)
        layout.addWidget(instr)

        self.table = QTableWidget(len(self._orig_values), 2)
        self.table.setHorizontalHeaderLabels(["Original Value", "New Group Name"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        for i, val in enumerate(self._orig_values):
            # Original value — read-only
            orig_item = QTableWidgetItem(str(val))
            orig_item.setFlags(orig_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(i, 0, orig_item)

            # Group name — editable; pre-fill from existing mapping or identity
            group = str(existing_mapping.get(val, val)) if existing_mapping else str(val)
            self.table.setItem(i, 1, QTableWidgetItem(group))

        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        # Quick-group helper row
        helper_layout = QHBoxLayout()
        helper_layout.addWidget(QLabel("Set selected rows to:"))
        from PyQt6.QtWidgets import QLineEdit
        self._quick_edit = QLineEdit()
        self._quick_edit.setPlaceholderText("group name …")
        quick_btn = QPushButton("Apply to selection")
        quick_btn.clicked.connect(self._apply_quick_group)
        helper_layout.addWidget(self._quick_edit, 1)
        helper_layout.addWidget(quick_btn)
        layout.addLayout(helper_layout)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        reset_btn = QPushButton("Reset to original")
        btn_box.addButton(reset_btn, QDialogButtonBox.ButtonRole.ResetRole)
        reset_btn.clicked.connect(self._reset)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _reset(self) -> None:
        for i, val in enumerate(self._orig_values):
            self.table.item(i, 1).setText(str(val))

    def _apply_quick_group(self) -> None:
        group_name = self._quick_edit.text().strip()
        if not group_name:
            return
        for item in self.table.selectedItems():
            if item.column() == 1:
                item.setText(group_name)

    def get_mapping(self) -> dict:
        """Return {original_value: group_name_str} preserving original value types as keys."""
        return {
            self._orig_values[i]: (
                self.table.item(i, 1).text().strip() or str(self._orig_values[i])
            )
            for i in range(self.table.rowCount())
        }
