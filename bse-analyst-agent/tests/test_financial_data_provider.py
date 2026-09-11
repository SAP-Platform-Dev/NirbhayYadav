import unittest

from src.financial_data_provider import StructuredFinancialProvider
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


if __name__ == "__main__":
    unittest.main()
