import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None))
sys.modules.setdefault("pandas", types.SimpleNamespace(isna=lambda value: value is None))
import daily_validation_report


class TradeIncidentReportingTests(unittest.TestCase):
    def test_incident_report_generated_for_blocked_trade(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            with patch.object(daily_validation_report, "REPORT_DIR", report_dir):
                report = daily_validation_report.log_trade_execution_incident(
                    trade_type="paper",
                    hard_block={
                        "blocker": "stale_dataset",
                        "reason": "master dataset stale",
                        "master_dataset_age_hours": 44.0,
                        "critical_alerts_active": [],
                        "supervision_verdict": "DO_NOT_RESUME_TRADING_OR_PAPER_TEST",
                    },
                    context={"price": 79039.0},
                    final={"position_usd": 3000.0},
                    portfolio={"btc_held": 0.03795595, "open_trades": 1, "cash_balance_usd": 7000.0},
                    real_order_sent=False,
                    recommendation="DO_NOT_RESUME",
                )

            json_path = report_dir / report["json_path"].split("/")[-1]
            md_path = report_dir / report["md_path"].split("/")[-1]

            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(data["trade_type"], "paper")
            self.assertFalse(data["real_order_sent"])
            self.assertEqual(data["entry_price"], 79039.0)
            self.assertEqual(data["position_usd"], 3000.0)
            self.assertEqual(data["risk_blocker"], "stale_dataset")
            self.assertEqual(data["stale_dataset_age_hours"], 44.0)
            self.assertEqual(data["supervision_verdict"], "DO_NOT_RESUME_TRADING_OR_PAPER_TEST")
            self.assertEqual(data["recommendation"], "DO_NOT_RESUME")
            self.assertIn("master dataset stale", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
