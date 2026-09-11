"""Reporting helpers for the equity research application.

This module owns file/report formatting only. It does not import the menu,
CLI entrypoint, scanner, or analysis orchestrator.
"""

import os
from datetime import datetime


def save_investment_summary(
    symbol,
    forensics,
    ratios,
    quality,
    valuation,
    recommendation,
    memo,
    output_dir="./outputs",
):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(output_dir, f"{symbol.upper()}_Investment_Summary_{timestamp}.txt")
    divider, sub = "=" * 70, "-" * 70

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"{divider}\nFIVE-YEAR EQUITY RESEARCH INVESTMENT MEMO\n")
        f.write(f"Company: {symbol.upper()} | Date: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}\n{divider}\n\n")
        f.write(f"[FINAL VERDICT]: {recommendation['verdict']}\n")
        f.write(f"[DETERMINISTIC QUALITY SCORE]: {quality['score_100']} / 100\n")
        f.write(f"[AI THESIS CONVICTION]: {memo.conviction_score} / 10\n")
        f.write(f"[GOVERNANCE]: {'PASSED' if memo.governance_clearance else 'FAILED / REVIEW'}\n")
        f.write(f"[DECISION LOGIC]: {recommendation['reason']}\n\n")
        f.write(f"{sub}\nEXECUTIVE THESIS\n{sub}\n{memo.executive_summary.strip()}\n\n")
        f.write(f"{sub}\nFIVE-YEAR FUNDAMENTALS\n{sub}\n")
        for metric, value in ratios.items():
            if metric != "hurdles_passed":
                f.write(f"  • {metric:<30}: {value}\n")
        f.write("\nHurdles:\n")
        for check, passed in ratios.get("hurdles_passed", {}).items():
            f.write(f"  • {check.replace('_', ' ').title():<30}: {'PASS [✓]' if passed else 'FAIL [X]'}\n")
        f.write(f"\n{sub}\nQUALITY SCORE\n{sub}\n")
        for component, points in quality["components"].items():
            f.write(f"  • {component.replace('_', ' ').title():<30}: {points:>2} / 20\n")
        f.write(f"  TOTAL: {quality['score_100']} / 100\n")
        f.write(f"\n{sub}\nVALUATION\n{sub}\n")
        if valuation.get("available"):
            for key, value in valuation.items():
                if key != "available":
                    f.write(f"  • {key.replace('_', ' ').title():<30}: {value}\n")
        else:
            f.write(f"  • {valuation.get('reason', 'Not calculated.')}\n")
        f.write(f"\n{sub}\nFORENSIC & GOVERNANCE\n{sub}\n")
        f.write(f"  • Audit Opinion             : {forensics.audit_opinion_type}\n")
        f.write(f"  • Contingent Liability Risk : {forensics.contingent_liability_risk}\n")
        f.write(f"  • Related Party Risk        : {forensics.related_party_risk}\n\n")
        f.write("  Key Audit Matters:\n")
        for item in forensics.key_audit_matters or ["None specified."]:
            f.write(f"    - {item}\n")
        f.write("\n  Forensic Red Flags:\n")
        for item in forensics.forensic_red_flags or ["None detected."]:
            f.write(f"    ! {item}\n")
        f.write(f"\n{sub}\nFINANCIAL STRENGTHS\n{sub}\n")
        for item in memo.financial_strengths:
            f.write(f"  [+] {item}\n")
        f.write(f"\n{sub}\nCRITICAL RISKS\n{sub}\n")
        for item in memo.critical_risks:
            f.write(f"  [-] {item}\n")
        f.write(f"\n{divider}\nEnd of Report\n")

    return filepath
