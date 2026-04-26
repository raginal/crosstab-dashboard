import pandas as pd
import numpy as np
from enum import Enum


class VariableType(Enum):
    NOMINAL = "Nominal"
    ORDINAL = "Ordinal"
    INTERVAL = "Interval/Ratio"


class VariableClassifier:
    """
    Auto-detects whether each column is Nominal, Ordinal, or Interval/Ratio.

    Heuristic priority:
      1. Non-numeric (object/category/bool) → Nominal
      2. Numeric with high cardinality (> 50% unique values, or > 20 distinct) → Interval
      3. Numeric matching a Likert-style integer scale (e.g. 1-5, 0-7) → Ordinal
      4. Numeric with ≤ 15 unique values (but not Likert) → Ordinal (conservative default)
      5. Everything else → Interval

    The analyst can always override via the UI.
    """

    ORDINAL_MAX_UNIQUE = 15
    INTERVAL_CARDINALITY_RATIO = 0.5

    def classify(self, series: pd.Series) -> VariableType:
        clean = series.dropna()
        if clean.empty:
            return VariableType.NOMINAL

        if series.dtype == bool or str(series.dtype) == 'boolean':
            return VariableType.NOMINAL

        if series.dtype == object or str(series.dtype) == 'category':
            return VariableType.NOMINAL

        if pd.api.types.is_numeric_dtype(series):
            n_unique = clean.nunique()
            n = len(clean)

            if n_unique / n > self.INTERVAL_CARDINALITY_RATIO or n_unique > 20:
                return VariableType.INTERVAL

            if self._is_likert_scale(clean):
                return VariableType.ORDINAL

            if n_unique <= self.ORDINAL_MAX_UNIQUE:
                return VariableType.ORDINAL

            return VariableType.INTERVAL

        return VariableType.NOMINAL

    def _is_likert_scale(self, series: pd.Series) -> bool:
        """True if the series looks like a contiguous integer rating scale (e.g. 1-5, 0-10)."""
        vals = series.dropna().unique()
        try:
            float_vals = [float(v) for v in vals]
        except (TypeError, ValueError):
            return False

        if not all(v == int(v) for v in float_vals):
            return False

        int_vals = sorted(int(v) for v in float_vals)
        n = len(int_vals)
        if n < 3 or n > 12:
            return False

        is_consecutive = (int_vals == list(range(int_vals[0], int_vals[-1] + 1)))
        starts_at_zero_or_one = int_vals[0] in (0, 1)
        ends_reasonably = int_vals[-1] in range(4, 13)

        return is_consecutive and starts_at_zero_or_one and ends_reasonably

    def classify_all(self, df: pd.DataFrame) -> dict[str, VariableType]:
        return {col: self.classify(df[col]) for col in df.columns}
