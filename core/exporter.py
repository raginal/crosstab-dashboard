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

    def export_table_png(self, display_df: pd.DataFrame, file_path: str, dpi: int = 150) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        nrows, ncols = display_df.shape
        fig_w = max(6, (ncols + 1) * 1.4)
        fig_h = max(2, nrows * 0.45 + 0.8)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        ax.axis("off")
        tbl = ax.table(
            cellText=display_df.fillna("").astype(str).values,
            rowLabels=display_df.index.tolist(),
            colLabels=display_df.columns.tolist(),
            loc="center",
            cellLoc="center",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.auto_set_column_width(col=list(range(ncols + 1)))
        fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    def export_figure(self, fig: plt.Figure, file_path: str, dpi: int = 150) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
