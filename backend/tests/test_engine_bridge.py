import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from backend.services.engine_bridge import get_portfolio_summary


def test_get_portfolio_summary_shape():
    summary = get_portfolio_summary()
    assert "portfolio_value" in summary
    assert "total_return_pct" in summary
    assert "positions" in summary
    assert "cash_pct" in summary
