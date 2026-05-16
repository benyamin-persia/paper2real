import json
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None))
import risk_engine


class RuntimeHardBlockTests(unittest.TestCase):
    def test_hard_block_triggers_on_stale_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "master_dataset.csv"
            dataset.write_text("timestamp,close\n2026-05-01,1\n", encoding="utf-8")
            old = time.time() - (40 * 3600)
            os.utime(dataset, (old, old))

            result = risk_engine.runtime_hard_block_active(
                master_dataset_path=dataset,
                max_dataset_age_hours=36,
                events_path=root / "missing_events.json",
                supervision_path=root / "missing_supervision.json",
            )

            self.assertTrue(result["active"])
            self.assertIn("stale_dataset", result["blockers"])
            self.assertGreater(result["master_dataset_age_hours"], 36)

    def test_hard_block_triggers_on_critical_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "master_dataset.csv"
            dataset.write_text("timestamp,close\n2026-05-15,1\n", encoding="utf-8")
            events = root / "events.json"
            events.write_text(
                json.dumps(
                    {
                        "has_critical": True,
                        "critical_alerts": [
                            {
                                "category": "EXCHANGE_RISK",
                                "severity": "CRITICAL",
                                "status": "active",
                                "message": "Exchange exploit alert",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = risk_engine.runtime_hard_block_active(
                master_dataset_path=dataset,
                max_dataset_age_hours=36,
                events_path=events,
                supervision_path=root / "missing_supervision.json",
            )

            self.assertTrue(result["active"])
            self.assertIn("critical_market_alert", result["blockers"])
            self.assertEqual(result["critical_alerts_active"][0]["category"], "EXCHANGE_RISK")

    def test_hard_block_triggers_on_supervision_do_not_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "master_dataset.csv"
            dataset.write_text("timestamp,close\n2026-05-15,1\n", encoding="utf-8")
            events = root / "events.json"
            events.write_text("{}", encoding="utf-8")
            supervision = root / "chatgpt_supervision_report.json"
            supervision.write_text(
                json.dumps({"supervision_verdict": "DO_NOT_RESUME_TRADING_OR_PAPER_TEST"}),
                encoding="utf-8",
            )

            result = risk_engine.runtime_hard_block_active(
                master_dataset_path=dataset,
                max_dataset_age_hours=36,
                events_path=events,
                supervision_path=supervision,
            )

            self.assertTrue(result["active"])
            self.assertIn("supervision_do_not_resume", result["blockers"])
            self.assertEqual(result["supervision_verdict"], "DO_NOT_RESUME_TRADING_OR_PAPER_TEST")


if __name__ == "__main__":
    unittest.main()
