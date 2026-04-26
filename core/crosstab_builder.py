import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CrosstabResult:
    """Raw contingency table data before formatting for display."""
    counts: pd.DataFrame         # full table including margins (Total row/col)
    col_pct: pd.DataFrame        # column-% for data cells only (no margins)
    row_vars: list[str]
    col_vars: list[str]
    n_total: int                 # unweighted sample size (always)
    aggfunc_col: Optional[str] = None
    aggfunc_name: Optional[str] = None
    weight_col: Optional[str] = None
    n_weighted: Optional[float] = None   # sum of weights; None when no weights applied


@dataclass
class DisplayResult:
    """Ready-to-render representation consumed by CrosstabPanel."""
    df: pd.DataFrame             # flat DataFrame with alternating N / % rows
    pct_row_indices: list[int]   # which row positions are percentage rows (for styling)
    total_row_index: int         # row position of the Total row
    total_col: str               # column name for the Total column


class CrosstabBuilder:
    """
    Builds contingency tables from a cleaned DataFrame.

    Supports:
      - 1 or 2 row variables
      - 1 or 2 column variables
      - Optional third variable with an aggregation function (mean / median / sum / count)
      - Optional weight column: weighted counts replace raw counts in the table;
        column percentages are computed from weighted counts.

    Statistical tests always run on unweighted data (independence of the
    observed sample).  The weighted table is for presentation of population
    estimates.  A note is added to the stats output when weights are active.

    When an aggfunc variable is used, statistical tests are disabled and no
    column-% rows are shown.
    """

    _AGG_FUNCS = {
        'mean':   np.mean,
        'median': np.median,
        'sum':    np.sum,
        'count':  len,
    }

    def build(
        self,
        df: pd.DataFrame,
        row_vars: list[str],
        col_vars: list[str],
        aggfunc_col: Optional[str] = None,
        aggfunc: str = 'mean',
        weight_col: Optional[str] = None,
    ) -> CrosstabResult:
        used = row_vars + col_vars + ([aggfunc_col] if aggfunc_col else [])
        if weight_col:
            used = used + [weight_col]
        df_clean = df[list(dict.fromkeys(used))].dropna()

        if df_clean.empty:
            raise ValueError(
                "No data remains after removing missing values for the selected variables."
            )

        for v in row_vars + col_vars:
            if df_clean[v].nunique() < 2:
                raise ValueError(
                    f"'{v}' has fewer than 2 unique values after cleaning — "
                    "cannot build a crosstab."
                )

        index_series = [df_clean[v] for v in row_vars]
        col_series   = [df_clean[v] for v in col_vars]
        n_total      = len(df_clean)
        n_weighted   = None

        if aggfunc_col:
            agg_fn = self._AGG_FUNCS.get(aggfunc, np.mean)
            counts = pd.crosstab(
                index=index_series,
                columns=col_series,
                values=df_clean[aggfunc_col],
                aggfunc=agg_fn,
                margins=True,
                margins_name='Total',
            ).round(2)
            col_pct = pd.DataFrame()

        elif weight_col:
            # Weighted counts = sum of weights per cell
            counts = pd.crosstab(
                index=index_series,
                columns=col_series,
                values=df_clean[weight_col],
                aggfunc='sum',
                margins=True,
                margins_name='Total',
            ).fillna(0).round(1)
            n_weighted = float(df_clean[weight_col].sum())
            # Column % from weighted counts
            data   = counts.iloc[:-1, :-1]
            totals = data.sum(axis=0).replace(0, np.nan)
            col_pct = (data.div(totals, axis=1) * 100).round(1)

        else:
            counts = pd.crosstab(
                index=index_series,
                columns=col_series,
                margins=True,
                margins_name='Total',
            )
            data   = counts.iloc[:-1, :-1]
            totals = data.sum(axis=0).replace(0, np.nan)
            col_pct = (data.div(totals, axis=1) * 100).round(1)

        if len(row_vars) == 1:
            counts.index.name = row_vars[0]
            if not col_pct.empty:
                col_pct.index.name = row_vars[0]
        if len(col_vars) == 1:
            counts.columns.name = col_vars[0]
            if not col_pct.empty:
                col_pct.columns.name = col_vars[0]

        return CrosstabResult(
            counts=counts,
            col_pct=col_pct,
            row_vars=row_vars,
            col_vars=col_vars,
            n_total=n_total,
            aggfunc_col=aggfunc_col,
            aggfunc_name=aggfunc if aggfunc_col else None,
            weight_col=weight_col,
            n_weighted=n_weighted,
        )

    def format_display(self, result: CrosstabResult) -> DisplayResult:
        counts = result.counts
        col_pct = result.col_pct
        is_aggfunc = result.aggfunc_col is not None

        def _flatten_key(k) -> str:
            return " / ".join(str(x) for x in k) if isinstance(k, tuple) else str(k)

        flat_cols = [_flatten_key(c) for c in counts.columns]

        rows_labels: list[str] = []
        rows_data:   list[dict] = []
        is_pct:      list[bool] = []

        non_total = counts.index[:-1]

        for idx in non_total:
            label  = _flatten_key(idx)
            n_label = label if is_aggfunc else f"{label}  N"

            n_row = {_flatten_key(c): counts.loc[idx, c] for c in counts.columns}
            rows_labels.append(n_label)
            rows_data.append(n_row)
            is_pct.append(False)

            if not is_aggfunc and not col_pct.empty and idx in col_pct.index:
                pct_row = {}
                for c in counts.columns:
                    fc = _flatten_key(c)
                    if fc == 'Total':
                        pct_row[fc] = ""
                    else:
                        val = col_pct.loc[idx, c] if c in col_pct.columns else np.nan
                        pct_row[fc] = "" if pd.isna(val) else f"{val:.1f}%"
                rows_labels.append(f"{label}  %")
                rows_data.append(pct_row)
                is_pct.append(True)

        total_row = {_flatten_key(c): counts.loc['Total', c] for c in counts.columns}
        rows_labels.append("Total")
        rows_data.append(total_row)
        is_pct.append(False)

        display_df = pd.DataFrame(rows_data, index=rows_labels, columns=flat_cols)

        pct_indices = [i for i, p in enumerate(is_pct) if p]
        total_index = len(rows_labels) - 1

        return DisplayResult(
            df=display_df,
            pct_row_indices=pct_indices,
            total_row_index=total_index,
            total_col='Total',
        )
