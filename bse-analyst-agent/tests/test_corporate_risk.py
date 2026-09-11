from src.corporate_risk import assess_corporate_risk


def test_high_pledge_is_hard_fail():
    result = assess_corporate_risk(
        promoter_holding_pct=45,
        promoter_pledge_pct=25,
        auditor_status="clean",
        related_party_risk="low",
    )
    assert result.hard_fail is True
    assert result.governance_grade == "D"


def test_missing_data_is_not_marked_safe():
    result = assess_corporate_risk()
    assert result.hard_fail is False
    assert result.data_gaps


def test_auditor_resignation_is_hard_fail():
    result = assess_corporate_risk(
        promoter_holding_pct=50,
        promoter_pledge_pct=0,
        auditor_status="auditor resignation",
        related_party_risk="low",
    )
    assert result.hard_fail is True


def test_clean_signals_receive_grade_a():
    result = assess_corporate_risk(
        promoter_holding_pct=55,
        promoter_pledge_pct=0,
        promoter_change_pct=1,
        auditor_status="clean",
        related_party_risk="low",
    )
    assert result.governance_grade == "A"


def test_generic_sebi_reference_has_no_risk_points():
    result = assess_corporate_risk(
        promoter_holding_pct=55,
        promoter_pledge_pct=0,
        promoter_change_pct=1,
        auditor_status="clean",
        related_party_risk="low",
        announcements=[{"subject": "SEBI disclosure under LODR", "details": "Routine corporate filing"}],
    )
    assert result.risk_score == 0
    assert result.governance_grade == "A"
    assert result.risk_flags == []


def test_sebi_regulatory_order_is_still_a_risk():
    result = assess_corporate_risk(
        promoter_holding_pct=55,
        promoter_pledge_pct=0,
        promoter_change_pct=1,
        auditor_status="clean",
        related_party_risk="low",
        announcements=[{"subject": "SEBI regulatory order", "details": "Penalty imposed"}],
    )
    assert result.risk_score == 20
    assert result.governance_grade == "B"
    assert "Corporate filing: regulatory order" in result.risk_flags
