import sys
import types
import unittest
from unittest.mock import patch

sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None))
sys.modules.setdefault("pandas", types.SimpleNamespace(isna=lambda value: value is None))
import shadow_paper_test


class ShadowPaperPauseTests(unittest.TestCase):
    def test_shadow_paper_test_paused_when_supervision_do_not_resume(self):
        with (
            patch.object(shadow_paper_test, "SHADOW_BUY_PAPER_TEST_ENABLED", True),
            patch.object(shadow_paper_test, "SHADOW_BUY_PAPER_TEST_MODE", "paper_only"),
            patch.object(shadow_paper_test, "SHADOW_BUY_PAPER_TEST_MIN_SHADOW_REVIEW_COUNT", 100),
            patch.object(
                shadow_paper_test.risk_engine,
                "supervision_hard_block",
                return_value={
                    "active": True,
                    "supervision_verdict": "DO_NOT_RESUME_TRADING_OR_PAPER_TEST",
                    "blocker": "supervision_do_not_resume",
                },
            ),
        ):
            review = {
                "final_shadow_buy_recommendation": shadow_paper_test.READY_RECOMMENDATION,
                "shadow_buy_count": 150,
            }

            self.assertFalse(shadow_paper_test._paper_test_entries_enabled(review))
            self.assertIn("Supervision forbids trading", shadow_paper_test._paper_test_pause_reason(review))


if __name__ == "__main__":
    unittest.main()
