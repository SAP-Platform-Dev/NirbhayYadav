from src.corporate_risk import CorporateRiskEngine, CorporateRiskResult, assess_corporate_risk


def test_engine_clean_company_is_grade_a():
    result = CorporateRiskEngine().assess(
        promoter_holding_pct=55,
        promoter_pledge_pct=0,
        promoter_change_pct=1,
        auditor_status="clean",
        related_party_risk="low",
    )
    assert isinstance(result, CorporateRiskResult)
    assert result.hard_fail is False
    assert result.governance_grade == "A"
    assert result.risk_score == 0


def test_high_pledge_is_hard_fail():
    result = CorporateRiskEngine().assess(
        promoter_holding_pct=40,
        promoter_pledge_pct=25,
        promoter_change_pct=0,
        auditor_status="clean",
        related_party_risk="low",
    )
    assert result.hard_fail is True
    assert result.governance_grade == "D"
    assert result.risk_score >= 35


def test_fraud_announcement_is_hard_fail():
    result = CorporateRiskEngine().assess(
        promoter_holding_pct=40,
        promoter_pledge_pct=0,
        promoter_change_pct=0,
        auditor_status="clean",
        related_party_risk="low",
        announcements=[{"subject": "Regulatory update", "details": "Forensic audit initiated after fraud concerns"}],
    )
    assert result.hard_fail is True
    assert any("fraud" in flag.lower() for flag in result.risk_flags)


def test_missing_governance_data_is_reported():
    result = CorporateRiskEngine().assess()
    assert result.hard_fail is False
    assert len(result.data_gaps) >= 4


def test_functional_api_remains_backward_compatible():
    result = assess_corporate_risk(promoter_holding_pct=60, promoter_pledge_pct=0)
    assert isinstance(result, CorporateRiskResult)
    assert result.risk_score == 0
