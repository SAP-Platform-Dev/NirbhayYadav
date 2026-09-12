from __future__ import annotations

import html
import os
import re
from pathlib import Path


def _escape(value: object) -> str:
    return html.escape(str(value))


def _read_text_report(report_file: str) -> str:
    path = Path(report_file)

    if not path.exists():
        raise FileNotFoundError(
            f"Investment decision report not found: {report_file}"
        )

    return path.read_text(encoding="utf-8")
def _read_governance_json(report_file: str) -> dict:
    report_path = Path(report_file)

    governance_file = (
        report_path.parent /
        "corporate_governance.json"
    )

    if not governance_file.exists():
        return {}

    import json

    try:
        return json.loads(
            governance_file.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {}
        

def _extract_value(text: str, label: str) -> str:
    pattern = rf"^{re.escape(label)}\s*:\s*(.+)$"

    match = re.search(
        pattern,
        text,
        re.MULTILINE,
    )

    return match.group(1).strip() if match else "N/A"


def _extract_section(
    text: str,
    section_name: str,
) -> str:
    pattern = (
        rf"{re.escape('-' * 72)}\n"
        rf"{re.escape(section_name)}\n"
        rf"{re.escape('-' * 72)}\n"
        rf"(.*?)(?=\n{re.escape('-' * 72)}|\Z)"
    )

    match = re.search(
        pattern,
        text,
        re.DOTALL,
    )

    return match.group(1).strip() if match else ""


def _extract_list(
    section: str,
    heading: str,
    marker: str = "-",
) -> list[str]:
    pattern = (
        rf"{re.escape(heading)}:\n"
        rf"(.*?)(?=\n\n|\Z)"
    )

    match = re.search(
        pattern,
        section,
        re.DOTALL,
    )

    if not match:
        return []

    values = []

    for line in match.group(1).splitlines():
        line = line.strip()

        if line.startswith(marker):
            value = line[1:].strip()

            if value:
                values.append(value)

    return values


def _extract_financial_history(text: str) -> list[dict[str, str]]:
    section = _extract_section(
        text,
        "FINANCIAL HISTORY USED",
    )

    if not section:
        return []

    rows = []

    started = False

    for line in section.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("Fiscal Year"):
            started = True
            continue

        if line.startswith("-" * 10):
            continue

        if not started:
            continue

        parts = re.split(r"\s{2,}", line)

        if len(parts) >= 4:
            rows.append(
                {
                    "year": parts[0],
                    "revenue": parts[1],
                    "ebit": parts[2],
                    "pat": parts[3],
                }
            )

    return rows


def _extract_financial_components(
    text: str,
) -> list[tuple[str, str]]:
    section = _extract_section(
        text,
        "FINANCIAL ANALYSIS",
    )

    if not section:
        return []

    components = []

    for line in section.splitlines():
        line = line.strip()

        if ":" not in line:
            continue

        if line.startswith("Financial Score"):
            continue

        name, value = line.rsplit(":", 1)

        name = name.strip()
        value = value.strip()

        if name and value:
            components.append(
                (name, value)
            )

    return components


def _extract_ratios(text: str) -> list[tuple[str, str]]:
    section = _extract_section(
        text,
        "FINANCIAL RATIOS",
    )

    if not section:
        return []

    ratios = []

    for line in section.splitlines():
        line = line.strip()

        if ":" not in line:
            continue

        name, value = line.rsplit(":", 1)

        name = name.strip()
        value = value.strip()

        if name and value:
            ratios.append(
                (name, value)
            )

    return ratios


def _score_class(score: str) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "neutral"

    if value >= 60:
        return "positive"

    if value >= 40:
        return "warning"

    return "negative"


def _verdict_class(verdict: str) -> str:
    verdict = verdict.upper()

    if verdict == "BUY":
        return "buy"

    if verdict == "WATCHLIST":
        return "watchlist"

    if verdict == "AVOID":
        return "avoid"

    return "neutral"


def generate_investment_report(
    report_file: str,
    output_file: str | None = None,
) -> str:
    """
    Generate a visual HTML investment report from
    investment_decision.txt.

    This module is presentation-only. It does not calculate
    or modify investment decisions.
    """

    text = _read_text_report(report_file)
    governance_data = _read_governance_json(report_file)
    report_path = Path(report_file)

    if output_file is None:
        output_file = str(
            report_path.with_name(
                "investment_report.html"
            )
        )

    symbol = _extract_value(
        text,
        "Stock",
    )

    generated = _extract_value(
        text,
        "Generated",
    )

    verdict = _extract_value(
        text,
        "VERDICT",
    )

    decision_score = _extract_value(
        text,
        "DECISION SCORE",
    )

    fundamental_score = _extract_value(
        text,
        "FUNDAMENTAL SCORE",
    )

    governance_score = _extract_value(
        text,
        "GOVERNANCE SCORE",
    )

    valuation_score = _extract_value(
        text,
        "VALUATION SCORE",
    )

    valuation_state = _extract_value(
        text,
        "VALUATION STATE",
    )

    reason_section = _extract_section(
        text,
        "FINAL INVESTMENT DECISION",
    )

    reason_match = re.search(
        r"REASON\s*\n\s*(.+)",
        reason_section,
    )

    reason = (
        reason_match.group(1).strip()
        if reason_match
        else "No decision reason available."
    )

    governance_section = _extract_section(
        text,
        "CORPORATE GOVERNANCE",
    )

    financial_history = _extract_financial_history(
        text
    )

    financial_components = _extract_financial_components(
        text
    )

    ratios = _extract_ratios(text)

    risk_flags = _extract_list(
        governance_section,
        "Risk Flags",
        "-",
    )

    positive_signals = _extract_list(
        governance_section,
        "Positive Signals",
        "+",
    )

    data_gaps = _extract_list(
        governance_section,
        "Data Gaps",
        "-",
    )

    annual_report_audits = governance_data.get(
        "annual_report_audits",
        [],
    )

    governance_grade = _extract_value(
        governance_section,
        "Governance Grade",
    )

    hard_fail = _extract_value(
        governance_section,
        "Hard Fail",
    )

    promoter_holding = _extract_value(
        governance_section,
        "Promoter Holding",
    )

    # ------------------------------------------------------------
    # Financial history chart
    # ------------------------------------------------------------

    chart_rows = ""

    for row in financial_history:
        chart_rows += f"""
        <tr>
            <td>{_escape(row["year"])}</td>
            <td>{_escape(row["revenue"])}</td>
            <td>{_escape(row["ebit"])}</td>
            <td>{_escape(row["pat"])}</td>
        </tr>
        """

    # ------------------------------------------------------------
    # Score cards
    # ------------------------------------------------------------

    scores = [
        (
            "Decision",
            decision_score,
            "decision",
        ),
        (
            "Fundamentals",
            fundamental_score,
            "fundamental",
        ),
        (
            "Governance",
            governance_score,
            "governance",
        ),
        (
            "Valuation",
            valuation_score,
            "valuation",
        ),
    ]

    score_cards = ""

    for name, value, css_class in scores:
        score_cards += f"""
        <div class="score-card">
            <div class="score-label">
                {_escape(name)}
            </div>

            <div class="score-value {css_class}">
                {_escape(value)}
            </div>
        </div>
        """

    # ------------------------------------------------------------
    # Financial components
    # ------------------------------------------------------------

    component_cards = ""

    for name, value in financial_components:
        component_cards += f"""
        <div class="component">
            <span>{_escape(name)}</span>
            <strong>{_escape(value)}</strong>
        </div>
        """

    # ------------------------------------------------------------
    # Ratios
    # ------------------------------------------------------------

    ratio_rows = ""

    for name, value in ratios:
        ratio_rows += f"""
        <tr>
            <td>{_escape(name)}</td>
            <td>{_escape(value)}</td>
        </tr>
        """

    # ------------------------------------------------------------
    # Governance lists
    # ------------------------------------------------------------

    def render_list(
        values: list[str],
        empty_text: str = "None",
    ) -> str:

        if not values:
            return (
                f'<div class="empty">{empty_text}</div>'
            )

        return "".join(
            f'<div class="list-item">{_escape(value)}</div>'
            for value in values
        )

    risk_html = render_list(
        risk_flags,
        "No governance risk flags recorded.",
    )
    # ------------------------------------------------------------
    # Detailed annual report forensic findings
    # ------------------------------------------------------------

    forensic_html = ""

    if annual_report_audits:

        for audit in annual_report_audits:

            fiscal_year = audit.get(
                "fiscal_year",
                "Unknown",
            )

            audit_opinion = audit.get(
                "audit_opinion_type",
                "Not available",
            )

            contingent_risk = audit.get(
                "contingent_liability_risk",
                "Not available",
            )

            related_party_risk = audit.get(
                "related_party_risk",
                "Not available",
            )

            red_flags = audit.get(
                "forensic_red_flags",
                [],
            )

            findings_html = ""

            if red_flags:

                for index, finding in enumerate(
                    red_flags,
                    start=1,
                ):
                    findings_html += f"""
                    <div class="forensic-finding">

                        <div class="finding-icon">
                            {index}
                        </div>

                        <div class="finding-text">
                            {_escape(finding)}
                        </div>

                    </div>
                    """

            else:

                findings_html = """
                <div class="empty">
                    No forensic red flags recorded.
                </div>
                """

            forensic_html += f"""
            <div class="audit-card">

                <div class="audit-header">

                    <div class="audit-year">
                        {_escape(fiscal_year)}
                    </div>

                    <div class="audit-opinion">
                        {_escape(audit_opinion)}
                    </div>

                </div>

                <div class="audit-risk-grid">

                    <div class="audit-risk">

                        <div class="audit-label">
                            Contingent Liability Risk
                        </div>

                        <div class="audit-value">
                            {_escape(contingent_risk)}
                        </div>

                    </div>

                    <div class="audit-risk">

                        <div class="audit-label">
                            Related Party Risk
                        </div>

                        <div class="audit-value">
                            {_escape(related_party_risk)}
                        </div>

                    </div>

                </div>

                <div class="findings-heading">
                    Forensic Red Flags
                </div>

                {findings_html}

            </div>
            """

    else:

        forensic_html = """
        <div class="empty">
            No annual report forensic audit data available.
        </div>
        """

    positive_html = render_list(
        positive_signals,
        "No positive governance signals recorded.",
    )

    gaps_html = render_list(
        data_gaps,
        "No data gaps recorded.",
    )

    verdict_css = _verdict_class(verdict)

    # ------------------------------------------------------------
    # HTML
    # ------------------------------------------------------------

    html_document = f"""<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
    {_escape(symbol)} Investment Report
</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family:
        Inter,
        Segoe UI,
        Arial,
        sans-serif;

    background:
        linear-gradient(
            135deg,
            #0b1020,
            #111827
        );

    color: #e5e7eb;
    line-height: 1.5;
}}

.container {{
    max-width: 1250px;
    margin: 0 auto;
    padding: 40px 24px 60px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 30px;
    margin-bottom: 30px;
}}

.brand {{
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 3px;
    color: #94a3b8;
}}

.title {{
    margin: 8px 0 4px;
    font-size: 42px;
    font-weight: 800;
}}

.subtitle {{
    color: #94a3b8;
}}

.verdict {{
    min-width: 220px;
    padding: 24px;
    border-radius: 18px;
    text-align: center;
    border: 1px solid rgba(255,255,255,.08);
}}

.verdict.buy {{
    background: rgba(34,197,94,.16);
}}

.verdict.watchlist {{
    background: rgba(234,179,8,.16);
}}

.verdict.avoid {{
    background: rgba(239,68,68,.16);
}}

.verdict.neutral {{
    background: rgba(148,163,184,.12);
}}

.verdict-label {{
    font-size: 12px;
    letter-spacing: 2px;
    color: #94a3b8;
}}

.verdict-value {{
    margin-top: 5px;
    font-size: 32px;
    font-weight: 900;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(4, 1fr);
    gap: 16px;
}}

.score-card {{
    background: rgba(255,255,255,.055);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 16px;
    padding: 22px;
}}

.score-label {{
    color: #94a3b8;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

.score-value {{
    margin-top: 8px;
    font-size: 34px;
    font-weight: 800;
}}

.score-value.decision {{
    color: #60a5fa;
}}

.score-value.fundamental {{
    color: #34d399;
}}

.score-value.governance {{
    color: #a78bfa;
}}

.score-value.valuation {{
    color: #fbbf24;
}}

.section {{
    margin-top: 28px;
    background: rgba(255,255,255,.045);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 18px;
    padding: 26px;
}}

.section h2 {{
    margin: 0 0 18px;
    font-size: 20px;
}}

.reason {{
    font-size: 18px;
    padding: 18px;
    border-left: 4px solid #60a5fa;
    background: rgba(96,165,250,.08);
    border-radius: 8px;
}}

.two-column {{
    display: grid;
    grid-template-columns:
        repeat(2, 1fr);
    gap: 20px;
}}

.component {{
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom:
        1px solid rgba(255,255,255,.07);
}}

.component:last-child {{
    border-bottom: none;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    text-align: left;
    color: #94a3b8;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

th,
td {{
    padding: 12px;
    border-bottom:
        1px solid rgba(255,255,255,.07);
}}

td:last-child {{
    font-weight: 700;
}}

.list-item {{
    padding: 12px 14px;
    margin-bottom: 8px;
    background: rgba(255,255,255,.045);
    border-radius: 8px;
}}

.empty {{
    color: #94a3b8;
    font-style: italic;
}}

.info-grid {{
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
    gap: 12px;
}}

.info {{
    padding: 15px;
    background: rgba(255,255,255,.045);
    border-radius: 10px;
}}

.info-label {{
    color: #94a3b8;
    font-size: 12px;
}}

.info-value {{
    margin-top: 4px;
    font-weight: 700;
}}
.audit-card {{
    margin-top: 18px;
    padding: 20px;
    background: rgba(255,255,255,.035);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 14px;
}}

.audit-card:first-child {{
    margin-top: 0;
}}

.audit-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 15px;
    margin-bottom: 18px;
}}

.audit-year {{
    font-size: 20px;
    font-weight: 800;
}}

.audit-opinion {{
    padding: 6px 10px;
    border-radius: 8px;
    background: rgba(34,197,94,.12);
    color: #86efac;
    font-size: 12px;
    font-weight: 700;
}}

.audit-risk-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}}

.audit-risk {{
    padding: 14px;
    background: rgba(255,255,255,.04);
    border-radius: 10px;
}}

.audit-label {{
    color: #94a3b8;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

.audit-value {{
    margin-top: 6px;
    font-size: 14px;
    line-height: 1.6;
}}

.findings-heading {{
    margin-bottom: 10px;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #fbbf24;
    font-weight: 700;
}}

.forensic-finding {{
    display: flex;
    gap: 12px;
    padding: 14px;
    margin-top: 8px;
    background: rgba(239,68,68,.07);
    border-left: 3px solid #ef4444;
    border-radius: 8px;
}}

.finding-icon {{
    min-width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: rgba(239,68,68,.18);
    color: #fca5a5;
    font-size: 12px;
    font-weight: 800;
}}

.finding-text {{
    color: #cbd5e1;
    font-size: 14px;
    line-height: 1.65;
}}
.footer {{
    margin-top: 40px;
    text-align: center;
    color: #64748b;
    font-size: 12px;
}}

@media (max-width: 850px) {{

    .header {{
        flex-direction: column;
    }}

    .verdict {{
        width: 100%;
    }}

    .grid,
    .two-column,
    .info-grid {{
        grid-template-columns: 1fr;
    }}

    .title {{
        font-size: 32px;
    }}

}}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <div>
            <div class="brand">
                NSE Equity Research Agent
            </div>

            <div class="title">
                {_escape(symbol)}
            </div>

            <div class="subtitle">
                Investment Decision Report
                · {_escape(generated)}
            </div>
        </div>

        <div class="verdict {verdict_css}">

            <div class="verdict-label">
                FINAL VERDICT
            </div>

            <div class="verdict-value">
                {_escape(verdict)}
            </div>

        </div>

    </div>


    <div class="grid">

        {score_cards}

    </div>


    <div class="section">

        <h2>
            Investment Thesis
        </h2>

        <div class="reason">
            {_escape(reason)}
        </div>

    </div>


    <div class="section">

        <h2>
            Decision Components
        </h2>

        <div class="two-column">

            <div>
                <div class="component">
                    <span>Fundamental Quality</span>
                    <strong>
                        {_escape(fundamental_score)}
                    </strong>
                </div>

                <div class="component">
                    <span>Governance</span>
                    <strong>
                        {_escape(governance_score)}
                    </strong>
                </div>

                <div class="component">
                    <span>Valuation</span>
                    <strong>
                        {_escape(valuation_score)}
                    </strong>
                </div>
            </div>

            <div>

                <div class="component">
                    <span>Valuation State</span>
                    <strong>
                        {_escape(valuation_state)}
                    </strong>
                </div>

                <div class="component">
                    <span>Governance Grade</span>
                    <strong>
                        {_escape(governance_grade)}
                    </strong>
                </div>

                <div class="component">
                    <span>Governance Hard Fail</span>
                    <strong>
                        {_escape(hard_fail)}
                    </strong>
                </div>

            </div>

        </div>

    </div>


    <div class="section">

        <h2>
            Financial Quality
        </h2>

        {component_cards}

    </div>


    <div class="section">

        <h2>
            Financial History
        </h2>

        <table>

            <thead>

                <tr>
                    <th>Fiscal Year</th>
                    <th>Revenue</th>
                    <th>EBIT</th>
                    <th>PAT</th>
                </tr>

            </thead>

            <tbody>

                {chart_rows}

            </tbody>

        </table>

    </div>


    <div class="section">

        <h2>
            Financial Ratios
        </h2>

        <table>

            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
            </thead>

            <tbody>

                {ratio_rows}

            </tbody>

        </table>

    </div>


    <div class="section">

        <h2>
            Corporate Governance
        </h2>

        <div class="info-grid">

            <div class="info">
                <div class="info-label">
                    Governance Grade
                </div>

                <div class="info-value">
                    {_escape(governance_grade)}
                </div>
            </div>

            <div class="info">
                <div class="info-label">
                    Promoter Holding
                </div>

                <div class="info-value">
                    {_escape(promoter_holding)}
                </div>
            </div>

            <div class="info">
                <div class="info-label">
                    Hard Fail
                </div>

                <div class="info-value">
                    {_escape(hard_fail)}
                </div>
            </div>

        </div>

    </div>


    <div class="section">

    <h2>
        Annual Report Forensic Findings
    </h2>

    <div class="subtitle">
        Detailed findings extracted from annual report governance audits.
    </div>

    {forensic_html}

</div>


    <div class="section">

        <h2>
            Positive Governance Signals
        </h2>

        {positive_html}

    </div>


    <div class="section">

        <h2>
            Data Gaps
        </h2>

        {gaps_html}

    </div>


    <div class="section">

        <h2>
            Financial Component Breakdown
        </h2>

        {component_cards}

    </div>


    <div class="footer">

        Generated by NSE Equity Research Agent<br>
        Presentation layer only — investment decision is produced
        by the deterministic decision engine.

    </div>

</div>

</body>

</html>
"""

    Path(output_file).write_text(
        html_document,
        encoding="utf-8",
    )

    return output_file