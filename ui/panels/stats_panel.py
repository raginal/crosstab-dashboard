import html as _html
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QSizePolicy,
)
from PyQt6.QtGui import QFont

from core.statistics import StatTestResult
from ui.palette import SIG_TRUE, SIG_FALSE, EFFECT_LABEL_COLORS, PRIMARY, GREY_500


class StatsPanel(QWidget):
    """
    Displays the statistical test results below the crosstab.

    Rendered as styled HTML inside a read-only QTextEdit so the analyst can
    copy individual values.  Interpretation labels (Negligible → Large) are
    shown alongside numeric values so no statistics background is required.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.text)
        self.clear()

    def clear(self) -> None:
        self.text.setHtml(
            f"<p style='color:{GREY_500}; font-family:\"Segoe UI\",Arial,sans-serif; "
            f"padding:12px;'>No results yet — run an analysis first.</p>"
        )

    def set_result(self, result: StatTestResult, n: int) -> None:
        sig_color = SIG_TRUE if result.is_significant else SIG_FALSE
        sig_text  = "Yes" if result.is_significant else "No"

        def _fmt_p(p) -> str:
            if p is None or np.isnan(p):
                return "—"
            return "< 0.001" if p < 0.001 else f"{p:.4f}"

        def _fmt_stat(s) -> str:
            return "—" if (s is None or np.isnan(s)) else f"{s:.4f}"

        lc = EFFECT_LABEL_COLORS.get(result.effect_size_label or "", GREY_500)

        html = f"""
        <html><body style="font-family:'Segoe UI',Arial,sans-serif; font-size:13px;
                           color:#334155; padding:8px;">

        <h3 style="margin:0 0 10px 0; color:#0F172A;">
            Statistical Results
            <span style="font-size:11px; font-weight:normal; color:{GREY_500};">
                &nbsp;(n&nbsp;=&nbsp;{n:,})
            </span>
        </h3>

        <table cellpadding="6" cellspacing="0"
               style="border-collapse:collapse; width:100%; border:1px solid #E2E8F0;">
          <tr style="background:#F1F5F9;">
            <td style="width:40%; font-weight:600; border-bottom:1px solid #E2E8F0;">
                Independence test</td>
            <td style="border-bottom:1px solid #E2E8F0;">{result.test_name}</td>
          </tr>
          <tr>
            <td style="font-weight:600; border-bottom:1px solid #E2E8F0;">
                Test statistic</td>
            <td style="border-bottom:1px solid #E2E8F0;">{_fmt_stat(result.statistic)}</td>
          </tr>
          <tr style="background:#F1F5F9;">
            <td style="font-weight:600; border-bottom:1px solid #E2E8F0;">p-value</td>
            <td style="border-bottom:1px solid #E2E8F0;">
                {_fmt_p(result.p_value)}</td>
          </tr>
          <tr>
            <td style="font-weight:600; border-bottom:1px solid #E2E8F0;">
                Significant?&nbsp;<span style="font-weight:normal; font-size:11px;">
                (α&nbsp;=&nbsp;0.05)</span></td>
            <td style="font-weight:700; color:{sig_color};
                       border-bottom:1px solid #E2E8F0;">{sig_text}</td>
          </tr>
        """

        if result.effect_size is not None and not np.isnan(result.effect_size):
            html += f"""
          <tr style="background:#F1F5F9;">
            <td style="font-weight:600; border-bottom:1px solid #E2E8F0;">
                Effect size</td>
            <td style="border-bottom:1px solid #E2E8F0;">
                {result.effect_size_name} &nbsp;=&nbsp;
                <b>{result.effect_size:.4f}</b>
                &nbsp;<span style="color:{lc};">({result.effect_size_label})</span>
            </td>
          </tr>
            """

        html += "</table>"

        # ── Spearman supplement (Ordinal × Ordinal) ──────────────────────────
        if "spearman" in result.additional:
            sp = result.additional["spearman"]
            sp_lc = EFFECT_LABEL_COLORS.get(sp.get("label", ""), GREY_500)
            html += f"""
        <h4 style="margin:16px 0 6px 0; color:#0F172A;">
            Ordinal Association: Spearman's ρ</h4>
        <table cellpadding="6" cellspacing="0"
               style="border-collapse:collapse; width:100%; border:1px solid #E2E8F0;">
          <tr style="background:#F1F5F9;">
            <td style="width:40%; font-weight:600; border-bottom:1px solid #E2E8F0;">
                ρ (rho)</td>
            <td style="border-bottom:1px solid #E2E8F0;">{sp['rho']:.4f}</td>
          </tr>
          <tr>
            <td style="font-weight:600; border-bottom:1px solid #E2E8F0;">p-value</td>
            <td style="border-bottom:1px solid #E2E8F0;">
                {'< 0.001' if sp['p_value'] < 0.001 else f"{sp['p_value']:.4f}"}</td>
          </tr>
          <tr style="background:#F1F5F9;">
            <td style="font-weight:600;">Strength</td>
            <td><span style="color:{sp_lc};">{sp['label']}</span></td>
          </tr>
        </table>
            """

        # ── Spearman check (Pearson supplement when both normal) ─────────────
        if "spearman_check" in result.additional:
            sp = result.additional["spearman_check"]
            sp_lc = EFFECT_LABEL_COLORS.get(sp.get("label", ""), GREY_500)
            html += f"""
        <h4 style="margin:16px 0 6px 0; color:#0F172A;">
            Supplemental: Spearman's ρ</h4>
        <p style="font-size:11px; color:{GREY_500}; margin:0 0 6px 0;">
            Included as a non-parametric reference alongside Pearson.</p>
        <table cellpadding="6" cellspacing="0"
               style="border-collapse:collapse; width:100%; border:1px solid #E2E8F0;">
          <tr style="background:#F1F5F9;">
            <td style="width:40%; font-weight:600; border-bottom:1px solid #E2E8F0;">
                ρ (rho)</td>
            <td style="border-bottom:1px solid #E2E8F0;">{sp['rho']:.4f}</td>
          </tr>
          <tr>
            <td style="font-weight:600; border-bottom:1px solid #E2E8F0;">p-value</td>
            <td style="border-bottom:1px solid #E2E8F0;">
                {'< 0.001' if sp['p_value'] < 0.001 else f"{sp['p_value']:.4f}"}</td>
          </tr>
          <tr style="background:#F1F5F9;">
            <td style="font-weight:600;">Strength</td>
            <td><span style="color:{sp_lc};">{sp['label']}</span></td>
          </tr>
        </table>
            """

        # ── Notes / warnings ─────────────────────────────────────────────────
        if result.notes:
            html += f"""
        <h4 style="margin:16px 0 6px 0; color:#0F172A;">Notes</h4>
        <ul style="margin:0; padding-left:18px;">
            """
            for note in result.notes:
                escaped = _html.escape(note)
                color = SIG_FALSE if ("⚠" in note or "WARNING" in note) else "#334155"
                info  = "#2563EB" if note.startswith("ℹ") else color
                html += f"<li style='color:{info}; margin-bottom:5px;'>{escaped}</li>"
            html += "</ul>"

        html += f"""
        <p style="font-size:11px; color:{GREY_500}; margin-top:14px; border-top:1px solid #E2E8F0;
                  padding-top:6px;">
            Significance levels: *** p&lt;0.001 &nbsp; ** p&lt;0.01 &nbsp;
            * p&lt;0.05 &nbsp; ns = not significant
        </p>
        </body></html>
        """

        self.text.setHtml(html)
