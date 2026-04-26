import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal

from core.data_loader import DataLoader


class FilePanel(QWidget):
    """
    Phase 1 of the workflow: load a CSV or Excel file.

    Emits data_loaded(df, file_path) once the file is successfully read.
    For Excel files, a sheet selector appears so the analyst can choose which
    worksheet to load.
    """

    data_loaded = pyqtSignal(object, str)  # (pd.DataFrame, file_path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loader = DataLoader()
        self._build_ui()

    def _build_ui(self) -> None:
        group = QGroupBox("Data File")
        g_layout = QVBoxLayout(group)

        # File path row
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("No file loaded…")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_btn)
        g_layout.addLayout(path_row)

        # Sheet selector (Excel only)
        sheet_row = QHBoxLayout()
        self.sheet_label = QLabel("Sheet:")
        self.sheet_combo = QComboBox()
        self.reload_btn = QPushButton("Load sheet")
        self.reload_btn.clicked.connect(self._load_selected_sheet)
        sheet_row.addWidget(self.sheet_label)
        sheet_row.addWidget(self.sheet_combo, 1)
        sheet_row.addWidget(self.reload_btn)
        self.sheet_label.setVisible(False)
        self.sheet_combo.setVisible(False)
        self.reload_btn.setVisible(False)
        g_layout.addLayout(sheet_row)

        # Status line
        self.status_label = QLabel("")
        g_layout.addWidget(self.status_label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open survey data",
            "",
            "Data files (*.csv *.xlsx *.xls);;CSV (*.csv);;Excel (*.xlsx *.xls)",
        )
        if not path:
            return

        self.path_edit.setText(path)
        sheets = self._loader.get_sheet_names(path)

        if sheets:
            self.sheet_combo.blockSignals(True)
            self.sheet_combo.clear()
            self.sheet_combo.addItems(sheets)
            self.sheet_combo.blockSignals(False)
            self.sheet_label.setVisible(True)
            self.sheet_combo.setVisible(True)
            self.reload_btn.setVisible(True)
            self._load_file(path, sheets[0])
        else:
            self.sheet_label.setVisible(False)
            self.sheet_combo.setVisible(False)
            self.reload_btn.setVisible(False)
            self._load_file(path, None)

    def _load_selected_sheet(self) -> None:
        path = self.path_edit.text()
        sheet = self.sheet_combo.currentText() or None
        if path:
            self._load_file(path, sheet)

    def _load_file(self, path: str, sheet: str | None) -> None:
        try:
            df = self._loader.load(path, sheet_name=sheet)
            n_rows, n_cols = df.shape
            self.status_label.setText(
                f"Loaded: {n_rows:,} rows × {n_cols} columns"
                + (f"  |  Sheet: {sheet}" if sheet else "")
            )
            self.data_loaded.emit(df, path)
        except Exception as exc:
            QMessageBox.critical(self, "Load error", str(exc))
            self.status_label.setText("Failed to load file.")
