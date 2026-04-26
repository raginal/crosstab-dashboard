"""
Statistical testing engine for the crosstab tool.

Test selection matrix:

  Row type  ×  Col type         Independence test            Effect size
  ──────────────────────────────────────────────────────────────────────
  Nominal   ×  Nominal          χ² / Fisher's exact          Cramér's V (bias-corrected)
  Nominal   ×  Ordinal          χ² / Fisher's exact          Cramér's V
  Ordinal   ×  Ordinal          χ² / Fisher's exact          Cramér's V + Spearman's ρ
  Interval  ×  Categorical      Mann-Whitney U (2 groups)    Rank-biserial r
                                Kruskal-Wallis (k > 2)       η² (eta-squared)
  Interval  ×  Interval         Pearson r  (if both normal)  Pearson's r
                                Spearman ρ (if non-normal)   Spearman's ρ

Normality testing for Interval × Interval:
  n < 3         → insufficient; use Spearman
  3 ≤ n ≤ 5000  → Shapiro-Wilk  (most powerful for small/medium samples)
  n > 5000      → D'Agostino-Pearson omnibus test  (scipy normaltest)
  Both normal (p > 0.05) → Pearson; otherwise → Spearman

Chi-square assumption check (every categorical × categorical test):
  ≥ 80% of expected cells must be ≥ 5, no expected cell < 1.
  Violated + 2×2 table → Fisher's exact.
  Violated + larger table → χ² with prominent warning.

Weighting:
  When weighted=True the test is still run on the raw (unweighted) sample.
  A note is appended to inform the analyst.  The weighted table is for
  presentation; the unweighted test is for valid statistical inference.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Tuple
from scipy.stats import (
    chi2_contingency, fisher_exact, kruskal, mannwhitneyu,
    spearmanr, pearsonr, shapiro, normaltest,
)

from .variable_classifier import VariableType


@dataclass
class StatTestResult:
    test_name: str
    statistic: float
    p_value: float
    is_significant: bool
    effect_size_name: Optional[str]
    effect_size: Optional[float]
    effect_size_label: Optional[str]
    notes: list[str] = field(default_factory=list)
    additional: dict = field(default_factory=dict)

    @property
    def sig_stars(self) -> str:
        if self.p_value is None or np.isnan(self.p_value):
            return ""
        if self.p_value < 0.001:
            return "***"
        if self.p_value < 0.01:
            return "**"
        if self.p_value < 0.05:
            return "*"
        return "ns"


class StatisticalTester:
    """
    Selects and runs the statistically appropriate test given variable types.

    For multi-variable selections (2 row or 2 col vars) the test is run on the
    combined contingency table using the primary (first) variable's types to
    determine which test family is appropriate.
    """

    ALPHA = 0.05

    def test(
        self,
        df: pd.DataFrame,
        row_vars: list[str],
        col_vars: list[str],
        var_types: dict[str, VariableType],
        weighted: bool = False,
    ) -> StatTestResult:
        primary_row = row_vars[0]
        primary_col = col_vars[0]
        row_type = var_types.get(primary_row, VariableType.NOMINAL)
        col_type = var_types.get(primary_col, VariableType.NOMINAL)

        used = list(dict.fromkeys(row_vars + col_vars))
        df_clean = df[used].dropna()

        if len(df_clean) < 5:
            return StatTestResult(
                test_name="Insufficient data",
                statistic=np.nan, p_value=np.nan, is_significant=False,
                effect_size_name=None, effect_size=None, effect_size_label=None,
                notes=["Fewer than 5 complete observations — cannot run a meaningful test."],
            )

        both_cat = (
            row_type in (VariableType.NOMINAL, VariableType.ORDINAL) and
            col_type in (VariableType.NOMINAL, VariableType.ORDINAL)
        )

        if both_cat:
            result = self._categorical(df_clean, row_vars, col_vars, row_type, col_type)
        elif row_type == VariableType.INTERVAL and col_type != VariableType.INTERVAL:
            result = self._interval_vs_cat(df_clean, primary_row, primary_col)
        elif col_type == VariableType.INTERVAL and row_type != VariableType.INTERVAL:
            result = self._interval_vs_cat(df_clean, primary_col, primary_row)
        else:
            result = self._interval_vs_interval(df_clean, primary_row, primary_col)

        if weighted:
            result.notes.insert(
                0,
                "ℹ Statistical test uses unweighted sample data. "
                "Weighted counts are shown in the table for population estimates. "
                "For design-based inference consider Rao-Scott adjusted χ².",
            )
        return result

    # ── Private test implementations ──────────────────────────────────────────

    def _categorical(
        self,
        df: pd.DataFrame,
        row_vars: list[str],
        col_vars: list[str],
        row_type: VariableType,
        col_type: VariableType,
    ) -> StatTestResult:
        notes: list[str] = []
        additional: dict = {}

        contingency = pd.crosstab(
            index=[df[v] for v in row_vars],
            columns=[df[v] for v in col_vars],
        )
        table = contingency.values.astype(float)
        n = int(table.sum())
        n_rows, n_cols = table.shape
        is_2x2 = (n_rows == 2 and n_cols == 2)

        # Assumption check
        _, _, _, expected = chi2_contingency(table, correction=False)
        pct_lt5  = float((expected < 5).mean())
        any_lt1  = bool((expected < 1).any())
        ok = pct_lt5 <= 0.20 and not any_lt1

        if not ok:
            notes.append(
                f"{pct_lt5 * 100:.0f}% of expected cells are < 5"
                + (" (at least one is < 1)" if any_lt1 else "")
                + " — chi-square assumptions violated."
            )

        if not ok and is_2x2:
            odds_ratio, p_val = fisher_exact(table, alternative='two-sided')
            stat = float(odds_ratio)
            test_name = "Fisher's Exact Test"
            notes.append(
                "Fisher's Exact Test used (2×2 table; assumptions not met). "
                "Statistic shown is the odds ratio."
            )
        else:
            correction = is_2x2
            chi2, p_val, dof, _ = chi2_contingency(table, correction=correction)
            stat = float(chi2)
            test_name = f"Chi-Square Test  (df = {dof})"
            if correction:
                notes.append("Yates' continuity correction applied (2×2 table).")
            if not ok and not is_2x2:
                notes.append(
                    "⚠ Chi-square assumptions not fully met for this table size. "
                    "Consider consolidating response categories to raise expected counts. "
                    "Interpret with caution."
                )

        v, v_label = self._cramers_v(table, n)
        is_sig = float(p_val) < self.ALPHA

        # Spearman supplement for Ordinal × Ordinal (single variables only)
        if (row_type == VariableType.ORDINAL and col_type == VariableType.ORDINAL
                and len(row_vars) == 1 and len(col_vars) == 1):
            row_codes = pd.Categorical(df[row_vars[0]]).codes.astype(float)
            col_codes = pd.Categorical(df[col_vars[0]]).codes.astype(float)
            rho, rho_p = spearmanr(row_codes, col_codes)
            additional['spearman'] = {
                'rho':     round(float(rho), 4),
                'p_value': round(float(rho_p), 4),
                'label':   self._label_r(abs(float(rho))),
            }
            notes.append(
                "Spearman's ρ included as a supplemental ordinal-association measure "
                "(captures the ordered relationship that χ² ignores)."
            )

        return StatTestResult(
            test_name=test_name,
            statistic=round(stat, 4),
            p_value=round(float(p_val), 4),
            is_significant=is_sig,
            effect_size_name="Cramér's V (bias-corrected)",
            effect_size=round(float(v), 4),
            effect_size_label=v_label,
            notes=notes,
            additional=additional,
        )

    def _interval_vs_cat(
        self, df: pd.DataFrame, interval_var: str, cat_var: str
    ) -> StatTestResult:
        notes = ["Non-parametric test used (interval variable compared across categorical groups)."]
        groups = [
            g[interval_var].dropna().values
            for _, g in df.groupby(cat_var)
            if len(g[interval_var].dropna()) > 0
        ]

        if len(groups) < 2:
            return StatTestResult(
                test_name="N/A", statistic=np.nan, p_value=np.nan, is_significant=False,
                effect_size_name=None, effect_size=None, effect_size_label=None,
                notes=["Need at least 2 non-empty groups."],
            )

        if any(len(g) < 5 for g in groups):
            notes.append("Some groups have < 5 observations — interpret results carefully.")

        if len(groups) == 2:
            stat, p_val = mannwhitneyu(groups[0], groups[1], alternative='two-sided')
            n1, n2 = len(groups[0]), len(groups[1])
            r = 1.0 - (2.0 * float(stat)) / (n1 * n2)
            return StatTestResult(
                test_name="Mann-Whitney U Test",
                statistic=round(float(stat), 4),
                p_value=round(float(p_val), 4),
                is_significant=float(p_val) < self.ALPHA,
                effect_size_name="Rank-biserial r",
                effect_size=round(abs(r), 4),
                effect_size_label=self._label_r(abs(r)),
                notes=notes,
            )

        stat, p_val = kruskal(*groups)
        n = sum(len(g) for g in groups)
        k = len(groups)
        eta2 = max(0.0, (float(stat) - k + 1) / (n - k))
        return StatTestResult(
            test_name=f"Kruskal-Wallis Test  (k = {k})",
            statistic=round(float(stat), 4),
            p_value=round(float(p_val), 4),
            is_significant=float(p_val) < self.ALPHA,
            effect_size_name="η²  (eta-squared)",
            effect_size=round(eta2, 4),
            effect_size_label=self._label_eta2(eta2),
            notes=notes,
        )

    def _interval_vs_interval(
        self, df: pd.DataFrame, v1: str, v2: str
    ) -> StatTestResult:
        """
        Choose Pearson or Spearman based on normality of both variables.

        Normality testing:
          3 ≤ n ≤ 5000  → Shapiro-Wilk
          n > 5000       → D'Agostino-Pearson omnibus test
          Both variables normal (p > 0.05) → Pearson r
          Otherwise                        → Spearman ρ
        """
        joint = df[[v1, v2]].dropna()
        x = joint[v1].values
        y = joint[v2].values
        n = len(x)
        notes: list[str] = []

        if n < 3:
            rho, p_val = spearmanr(x, y)
            notes.append("Sample too small for normality testing — Spearman used.")
            return StatTestResult(
                test_name="Spearman Rank Correlation",
                statistic=round(float(rho), 4),
                p_value=round(float(p_val), 4),
                is_significant=float(p_val) < self.ALPHA,
                effect_size_name="Spearman's ρ",
                effect_size=round(abs(float(rho)), 4),
                effect_size_label=self._label_r(abs(float(rho))),
                notes=notes,
            )

        # Select normality test
        if n <= 5000:
            norm_test_name = "Shapiro-Wilk"
            _, px = shapiro(x)
            _, py = shapiro(y)
        else:
            norm_test_name = "D'Agostino-Pearson"
            _, px = normaltest(x)
            _, py = normaltest(y)

        both_normal = float(px) > self.ALPHA and float(py) > self.ALPHA

        notes.append(
            f"Normality ({norm_test_name}): {v1} p = {px:.3f}, {v2} p = {py:.3f}. "
            + ("Both normally distributed → Pearson correlation used."
               if both_normal
               else "At least one variable is non-normal → Spearman correlation used.")
        )

        if n > 1000:
            notes.append(
                f"Note: with n = {n:,}, normality tests have very high power and may "
                "detect trivially small deviations.  Pearson is asymptotically robust "
                "for large samples regardless, but Spearman is still used when normality "
                "is rejected to remain conservative."
            )

        if both_normal:
            r_val, p_val = pearsonr(x, y)
            additional = {}
            # Include Spearman as a supplemental check
            rho, rho_p = spearmanr(x, y)
            additional['spearman_check'] = {
                'rho':     round(float(rho), 4),
                'p_value': round(float(rho_p), 4),
                'label':   self._label_r(abs(float(rho))),
            }
            return StatTestResult(
                test_name="Pearson Correlation",
                statistic=round(float(r_val), 4),
                p_value=round(float(p_val), 4),
                is_significant=float(p_val) < self.ALPHA,
                effect_size_name="Pearson's r",
                effect_size=round(abs(float(r_val)), 4),
                effect_size_label=self._label_r(abs(float(r_val))),
                notes=notes,
                additional=additional,
            )

        rho, p_val = spearmanr(x, y)
        return StatTestResult(
            test_name="Spearman Rank Correlation",
            statistic=round(float(rho), 4),
            p_value=round(float(p_val), 4),
            is_significant=float(p_val) < self.ALPHA,
            effect_size_name="Spearman's ρ",
            effect_size=round(abs(float(rho)), 4),
            effect_size_label=self._label_r(abs(float(rho))),
            notes=notes,
        )

    # ── Effect-size helpers ────────────────────────────────────────────────────

    def _cramers_v(self, table: np.ndarray, n: int) -> Tuple[float, str]:
        """Bias-corrected Cramér's V (Bergsma 2013)."""
        chi2 = chi2_contingency(table, correction=False)[0]
        r, c = table.shape
        phi2 = chi2 / n
        phi2corr = max(0.0, phi2 - ((c - 1) * (r - 1)) / (n - 1))
        rcorr = r - (r - 1) ** 2 / (n - 1)
        ccorr = c - (c - 1) ** 2 / (n - 1)
        denom = min(rcorr - 1, ccorr - 1)
        if denom <= 0:
            return 0.0, "N/A"
        v = float(np.sqrt(phi2corr / denom))
        return v, self._label_cramers_v(v, min(r, c) - 1)

    def _label_cramers_v(self, v: float, k: int) -> str:
        # Lovakov & Agadullina (2021) df-adjusted thresholds
        thresholds = {
            1: (0.10, 0.30, 0.50),
            2: (0.07, 0.21, 0.35),
            3: (0.06, 0.17, 0.29),
        }
        lo, md, hi = thresholds.get(k, (0.05, 0.15, 0.25))
        if v < lo: return "Negligible"
        if v < md: return "Small"
        if v < hi: return "Medium"
        return "Large"

    def _label_r(self, r: float) -> str:
        if r < 0.10: return "Negligible"
        if r < 0.30: return "Small"
        if r < 0.50: return "Medium"
        return "Large"

    def _label_eta2(self, eta2: float) -> str:
        if eta2 < 0.01: return "Negligible"
        if eta2 < 0.06: return "Small"
        if eta2 < 0.14: return "Medium"
        return "Large"
