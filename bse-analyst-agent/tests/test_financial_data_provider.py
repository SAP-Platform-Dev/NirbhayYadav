import unittest
from unittest.mock import Mock

from src.financial_data_provider import StructuredFinancialProvider
from src.financial_tools import calculate_fundamental_ratios
from src.financial_tools import AnnualFinancials


def make_record(year: int) -> AnnualFinancials:
    return AnnualFinancials(
        fiscal_year=f"FY{year}",
        revenue=100 + year,
        ebit=20,
        pat=10,
        total_debt=5,
        total_equity=100,
        cash_equivalents=2,
        cfo=12,
        interest_expense=1,
    )


class FinancialDataProviderTests(unittest.TestCase):
    def test_more_than_ten_years_trimmed_to_latest_ten(self):
        records = [make_record(year) for year in range(2014, 2027)]
        trimmed = StructuredFinancialProvider._reliable_records(records)
        self.assertEqual(len(trimmed), 10)
        self.assertEqual(trimmed[0].fiscal_year, "FY2017")
        self.assertEqual(trimmed[-1].fiscal_year, "FY2026")

    def test_parser_accepts_history_with_optional_cash_row_missing(self):
        html = """
        <section id="profit-loss">
          <table>
            <tr><th></th><th>Mar 2024</th><th>Mar 2025</th><th>Mar 2026</th></tr>
            <tr><td>Sales</td><td>100</td><td>120</td><td>140</td></tr>
            <tr><td>Operating Profit</td><td>20</td><td>24</td><td>28</td></tr>
            <tr><td>Interest</td><td>2</td><td>2</td><td>2</td></tr>
            <tr><td>Net Profit</td><td>10</td><td>12</td><td>14</td></tr>
          </table>
        </section>
        <section id="balance-sheet">
          <table>
            <tr><th></th><th>Mar 2024</th><th>Mar 2025</th><th>Mar 2026</th></tr>
            <tr><td>Equity Capital</td><td>10</td><td>10</td><td>10</td></tr>
            <tr><td>Reserves</td><td>90</td><td>110</td><td>130</td></tr>
            <tr><td>Borrowings</td><td>30</td><td>28</td><td>26</td></tr>
            <tr><td>Investments</td><td>5</td><td>6</td><td>7</td></tr>
          </table>
        </section>
        <section id="cash-flow">
          <table>
            <tr><th></th><th>Mar 2024</th><th>Mar 2025</th><th>Mar 2026</th></tr>
            <tr><td>Cash from Operating Activity</td><td>11</td><td>13</td><td>15</td></tr>
          </table>
        </section>
        """
        response = Mock(text=html)
        response.raise_for_status = Mock()
        provider = StructuredFinancialProvider()
        provider.session.get = Mock(return_value=response)

        history = provider._parse_screener("KCP", "https://example.test/KCP")
        ratios = calculate_fundamental_ratios(history)

        self.assertEqual(len(history.years), 3)
        self.assertIsNone(history.years[-1].cash_equivalents)
        self.assertIsNone(ratios["Net Debt (Cr)"])
        self.assertIsNone(ratios["ROCE (%)"])
        self.assertIsNotNone(ratios["Revenue CAGR 3Y (%)"])


if __name__ == "__main__":
    unittest.main()
