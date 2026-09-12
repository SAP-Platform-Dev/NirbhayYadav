import unittest

from src.decision_engine import calculate_investment_decision


class DecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.ratios = {"Positive CFO Years": "5/5"}
        self.quality = {
            "score_100": 80,
            "components": {
                "capital_efficiency": 20,
                "growth": 15,
                "balance_sheet": 15,
                "cash_quality": 20,
                "governance": 10,
            },
        }

    def test_margin_of_safety_can_produce_buy(self):
        valuation = {
            "available": True,
            "current_price": 60,
            "fair_value": 100,
            "buy_below": 70,
        }
        decision = calculate_investment_decision(
            self.quality, self.ratios, valuation, governance_grade="A", forensic_clean=True
        )
        self.assertEqual(decision["verdict"], "BUY")
        self.assertEqual(decision["valuation_state"], "MARGIN_OF_SAFETY")
        self.assertEqual(decision["decision_score"], 90)

    def test_above_fair_value_becomes_watchlist(self):
        valuation = {
            "available": True,
            "current_price": 105,
            "fair_value": 100,
            "buy_below": 70,
        }
        decision = calculate_investment_decision(
            self.quality, self.ratios, valuation, governance_grade="A", forensic_clean=True
        )
        self.assertEqual(decision["verdict"], "WATCHLIST")
        self.assertEqual(decision["valuation_state"], "ABOVE_FAIR_VALUE")

    def test_forensic_failure_is_hard_avoid(self):
        decision = calculate_investment_decision(
            self.quality, self.ratios, {"available": True, "current_price": 50, "fair_value": 100, "buy_below": 70},
            governance_grade="A", forensic_clean=False
        )
        self.assertEqual(decision["verdict"], "AVOID")
        self.assertIn("Forensic/governance", decision["reason"])

    def test_weak_fundamentals_are_avoid(self):
        quality = {"score_100": 30, "components": {"capital_efficiency": 8, "growth": 0, "balance_sheet": 0, "cash_quality": 0, "governance": 20}}
        decision = calculate_investment_decision(
            quality, self.ratios, {"available": True, "current_price": 20, "fair_value": 100, "buy_below": 70},
            governance_grade="A", forensic_clean=True
        )
        self.assertEqual(decision["verdict"], "AVOID")

    def test_persistent_cash_flow_failure_is_avoid(self):
        decision = calculate_investment_decision(
            self.quality, {"Positive CFO Years": "0/5"}, None,
            governance_grade="A", forensic_clean=True
        )
        self.assertEqual(decision["verdict"], "AVOID")


if __name__ == "__main__":
    unittest.main()
