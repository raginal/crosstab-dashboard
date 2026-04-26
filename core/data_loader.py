import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    """Loads survey data from CSV or Excel files into a pandas DataFrame."""

    SUPPORTED = {'.csv', '.xlsx', '.xls'}

    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.file_path: Optional[Path] = None

    def get_sheet_names(self, file_path: str) -> list[str]:
        path = Path(file_path)
        if path.suffix.lower() in {'.xlsx', '.xls'}:
            return pd.ExcelFile(path).sheet_names
        return []

    def load(self, file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED:
            raise ValueError(
                f"Unsupported file type '{path.suffix}'. Please use CSV, XLSX, or XLS."
            )

        self.file_path = path

        if ext == '.csv':
            self.df = pd.read_csv(path, low_memory=False)
        else:
            engine = 'openpyxl' if ext == '.xlsx' else 'xlrd'
            if sheet_name is None:
                sheet_name = self.get_sheet_names(file_path)[0]
            try:
                self.df = pd.read_excel(path, sheet_name=sheet_name, engine=engine)
            except TypeError as exc:
                # openpyxl 3.1.0 renamed WorksheetProperties.synchVertical → syncVertical
                # without preserving the old spelling, breaking files that contain it.
                if 'synchVertical' in str(exc) or 'synchHorizontal' in str(exc):
                    raise ValueError(
                        "Excel file contains a worksheet property that is incompatible "
                        "with your installed version of openpyxl.\n\n"
                        "Fix — run one of:\n"
                        "  pip install 'openpyxl>=3.0.9,<3.1.0'\n"
                        "  pip install --upgrade openpyxl\n\n"
                        f"(original error: {exc})"
                    ) from None
                raise

        return self.df
