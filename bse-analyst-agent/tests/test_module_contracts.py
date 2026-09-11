from src.contracts import PUBLIC_MODULE_APIS


def test_public_module_api_contract_is_complete():
    expected = {
        "discovery",
        "risk",
        "annual_report",
        "document_parser",
        "financial_ratios",
        "quality_score",
        "valuation",
        "recommendation",
        "deep_scan",
        "reporting",
    }
    assert set(PUBLIC_MODULE_APIS) == expected


def test_public_module_apis_do_not_depend_on_menu_or_main():
    assert all("src.menu" not in path for path in PUBLIC_MODULE_APIS.values())
    assert all(path != "main" and not path.startswith("main.") for path in PUBLIC_MODULE_APIS.values())
