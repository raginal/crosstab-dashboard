import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


class Exporter:
    """Handles export of tables and charts to disk."""

    def export_table_excel(self, display_df: pd.DataFrame, file_path: str) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            display_df.to_excel(writer, sheet_name='Crosstab')

    def export_table_csv(self, display_df: pd.DataFrame, file_path: str) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        display_df.to_csv(path)

    def export_figure(self, fig: plt.Figure, file_path: str, dpi: int = 150) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
