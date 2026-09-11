import unittest

from src.financial_engine import FinancialAnalysisEngine, FinancialAnalysisResult
from src.financial_tools import AnnualFinancials, CompanyFinancialHistory


class TestFinancialAnalysisEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FinancialAnalysisEngine()
        self.history = CompanyFinancialHistory(
            years=[
                AnnualFinancials(
                    fiscal_year="FY2022",
                    revenue=100,
                    ebit=20,
                    pat=12,
                    total_debt=20,
                    total_equity=80,
                    cash_equivalents=10,
                    cfo=14,
                    interest_expense=3,
                    capex=5,
                ),
                AnnualFinancials(
                    fiscal_year="FY2023",
                    revenue=120,
                    ebit=25,
                    pat=15,
                    total_debt=18,
                    total_equity=90,
                    cash_equivalents=12,
                    cfo=17,
                    interest_expense=3,
                    capex=5,
                ),
                AnnualFinancials(
                    fiscal_year="FY2024",
                    revenue=145,
                    ebit=32,
                    pat=20,
                    total_debt=15,
                    total_equity=105,
                    cash_equivalents=20,
                    cfo=23,
                    interest_expense=3,
                    capex=6,
                ),
            ]
        )

    def test_analyze_returns_stable_result(self):
        result = self.engine.analyze(
            self.history,
            governance_clean=True,
            current_price=100,
            shares_outstanding_cr=1,
        )
        self.assertIsInstance(result, FinancialAnalysisResult)
        self.assertIn("ROCE (%)", result.ratios)
        self.assertIn("score_100", result.quality)
        self.assertTrue(result.valuation["available"])
        self.assertIn("verdict", result.recommendation)

    def test_missing_valuation_inputs_do_not_break_analysis(self):
        result = self.engine.analyze(self.history, governance_clean=True)
        self.assertFalse(result.valuation["available"])
        self.assertIn("verdict", result.recommendation)

    def test_governance_failure_removes_governance_points(self):
        result = self.engine.analyze(self.history, governance_clean=False)
        self.assertEqual(result.quality["components"]["governance"], 0)

    def test_old_functional_contracts_remain_usable(self):
        ratios = self.engine.calculate_ratios(self.history)
        quality = self.engine.calculate_quality(ratios, governance_clean=True)
        recommendation = self.engine.determine_recommendation(
            quality, ratios, True, {"available": False}
        )
        self.assertIn("score_100", quality)
        self.assertIn("verdict", recommendation)


if __name__ == "__main__":
    unittest.main()
