import pandas as pd
from typing import Optional


class ResponseConsolidator:
    """
    Manages response recoding (consolidation) for one or more columns.

    A mapping for a column is a dict of {original_value: new_group_name}.
    Example: {'TX': 'TX', 'CA': 'Other', 'AL': 'Other'} collapses all
    non-TX states into an 'Other' category.

    Keys must match the actual dtype of the column (int keys for int columns,
    str keys for object columns, etc.).  The dialog always returns the correct
    types because it stores the original values—not their string representations.
    """

    def __init__(self):
        self._mappings: dict[str, dict] = {}

    def set_mapping(self, column: str, value_to_group: dict) -> None:
        self._mappings[column] = value_to_group

    def remove_mapping(self, column: str) -> None:
        self._mappings.pop(column, None)

    def has_mapping(self, column: str) -> bool:
        return column in self._mappings

    def get_mapping(self, column: str) -> Optional[dict]:
        return self._mappings.get(column)

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of df with all active mappings applied."""
        df_out = df.copy()
        for col, mapping in self._mappings.items():
            if col not in df_out.columns:
                continue
            df_out[col] = df_out[col].map(
                lambda x, m=mapping: m.get(x, x) if pd.notna(x) else x
            )
        return df_out

    def set_from_dict(self, mappings: dict[str, dict]) -> None:
        """Replace all mappings at once (called by MainWindow from config dict)."""
        self._mappings = dict(mappings)

    def clear(self) -> None:
        self._mappings.clear()
