# Paper2Real ChatGPT Supervision Report

Snapshot ID: `c1d542f6545f74eb`
Bundle generated at: `2026-05-15T06:35:09.947059+00:00`
Source commit SHA: `443bc6beb11a44cce93a923e0969de092ef8173a`

## Executive Verdict

**DO NOT RESUME Shadow Paper Test. Do not enable bonuses. Do not change trading logic.**

- Supervision verdict: `DO_NOT_RESUME_TRADING_OR_PAPER_TEST`
- Count consistency: `PASS`
- System health: `ok`
- Stale dataset warning: `False`
- Real trades executed: `0`
- Paper test status: `Paper Test Paused`
- Paper entries enabled: `False`
- Final risk recommendation: `KEEP_AS_IS`
- Final Smart Money recommendation: `SMART_MONEY_STAYS_SHADOW`
- Smart Money minimum sample reached: `True`
- Smart Money bonus approved: `False`
- Final Shadow BUY recommendation: `SHADOW_BUY_STAYS_SHADOW`
- TA ready for bonus: `False`
- AI TA ready for bonus: `False`
- Strict resume recommendation: `DO_NOT_RESUME_YET`

## Machine Entry Point

- Machine source of truth: `data/reports/chatgpt_supervision_report.json`
- Human source of truth: `CHATGPT_SUPERVISION_REPORT.md`
- Use commit-pinned URLs for immutable audits. Branch URLs are convenient but mutable.

## Validation Checklist

- `PASS` System health is ok (daily_validation_report.json: system_health_status)
- `PASS` Dataset is not stale (daily_validation_report.json: stale_dataset_warning)
- `PASS` Download ZIP is safe (daily_validation_report.json: download_zip_safe)
- `PASS` Secrets excluded (daily_validation_report.json: secrets_excluded)
- `PASS` No real trades executed (daily_validation_report.json: trades_executed)
- `PASS` Paper test entries disabled (shadow_paper_test_report.json)
- `PASS` Paper test has no open trades (shadow_paper_test_report.json)
- `PASS` Risk engine recommendation is keep as-is (risk_block_review.json)
- `PASS` Smart Money remains shadow-only (smart_money_review.json)
- `PASS` Shadow BUY remains shadow-only (shadow_buy_review.json)
- `PASS` Shadow BUY positive expectancy is false (shadow_buy_review.json)
- `PASS` TA bonus not ready/enabled (daily_validation_report.json)
- `PASS` AI TA bonus not ready/enabled (daily_validation_report.json)
- `PASS` Strict resume says do not resume (strict_resume_shadow_simulation.json)
- `PASS` Report counts are consistent (count_consistency)
- `PASS` All required exported paths exist (required_reports)

## Count Consistency

- `PASS` shadow_buy_count: `{"daily.shadow_buy_count": 209, "daily.shadow_buy_review_count": 209, "shadow_buy_failure_diagnosis.total_shadow_buy_records": 209, "shadow_buy_review.shadow_buy_count": 209, "shadow_paper_test.shadow_buy_review_count": 209, "strict_resume_shadow_simulation.total_shadow_buy_records": 209}`
- `PASS` risk_blocked_candidates: `{"daily.risk_blocked_candidates": 187, "risk_block_review.total_blocked_candidates": 187}`
- `PASS` smart_money_shadow_count: `{"daily.shadow_smart_money_count": 175, "smart_money_review.smart_money_shadow_count": 175}`

## Required Report Inventory

- `data/reports/daily_validation_report.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:09.925701+00:00`
  - Metric scope: canonical daily system health, endpoint, safety, learning, TA, and AI TA summary snapshot
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/daily_validation_report.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/daily_validation_report.json
  - SHA-256: `f8d9a76b32bcaf9f0293afbd468b0214bc5c8eda312e24763884c289da3421c4`
- `data/reports/daily_validation_report.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable daily validation summary
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/daily_validation_report.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/daily_validation_report.md
  - SHA-256: `4911fde4e8047414f75c3dceb6d369fa66e58ed3998d1304bf48ecdbf901c437`
- `data/reports/risk_block_review.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:06.979828+00:00`
  - Metric scope: risk-blocked candidate review from decisions.risk_blocked_candidate rows
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/risk_block_review.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/risk_block_review.json
  - SHA-256: `52d9af264f9458cd97af9389998a30b5e3e37329607d9ce629ea60c448be8f9a`
- `data/reports/risk_block_review.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable risk-blocked candidate review
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/risk_block_review.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/risk_block_review.md
  - SHA-256: `f0080ca078f96770e9a6fe46833ab0ad38ff5c9e2eaa1bdf587812c602435712`
- `data/reports/smart_money_review.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:06.847988+00:00`
  - Metric scope: Smart Money shadow evidence review; not an execution approval
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/smart_money_review.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/smart_money_review.json
  - SHA-256: `c73a1e4783e3e99114c58d8f45a6a0329c15b33daba1b91322a32ea7f2124b86`
- `data/reports/smart_money_review.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Smart Money shadow review
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/smart_money_review.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/smart_money_review.md
  - SHA-256: `c64601e8b745335ae80e374c638c82f68f9307a6db445f877978a6c98a88df24`
- `data/reports/shadow_buy_review.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:09.043804+00:00`
  - Metric scope: Shadow BUY evidence review from decisions.shadow_action=BUY rows
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_review.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_review.json
  - SHA-256: `761c6bae411e05b88bf0d3ce1982ae0ad2df9385cf8751d3e76406cd5c0d555d`
- `data/reports/shadow_buy_review.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Shadow BUY review
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_review.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_review.md
  - SHA-256: `3fa62a21c29c89fbfe7de270a4f79d8081b0279f3273f29054d697c54991bb00`
- `data/reports/shadow_paper_test_report.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:09.047176+00:00`
  - Metric scope: paper-only Shadow Paper Test lifecycle and paused-entry state
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_test_report.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_test_report.json
  - SHA-256: `493613e0acba348c50b1337dcadeab9ee3b19a870dd18f723df82b71ac6255c9`
- `data/reports/shadow_paper_test_report.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Shadow Paper Test state
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_test_report.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_test_report.md
  - SHA-256: `417d881c2c21c11f7c4d256ae919f565ba70ed0b6b9916854a296e1e275e0050`
- `data/reports/shadow_buy_failure_diagnosis.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:09.367331+00:00`
  - Metric scope: read-only failure diagnosis across Shadow BUY records and paper trades
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_failure_diagnosis.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_failure_diagnosis.json
  - SHA-256: `50ec4bb67c0b9d99eb22ce5ebc6a8a05f97ab77efae846862d46596f0f7c2e1c`
- `data/reports/shadow_buy_failure_diagnosis.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Shadow BUY failure diagnosis
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_failure_diagnosis.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_failure_diagnosis.md
  - SHA-256: `faa07c71740dc6a51c793e7b8d4cb8932221fc7b8c5fc079da06b005aa00ef0a`
- `data/reports/strict_resume_shadow_simulation.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:09.791131+00:00`
  - Metric scope: read-only staged strict-resume simulation; no entries are enabled
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/strict_resume_shadow_simulation.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/strict_resume_shadow_simulation.json
  - SHA-256: `b829f1f0fbbecab415c741346825c9d52167b892bcb5c4e41411f8922b382f09`
- `data/reports/strict_resume_shadow_simulation.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable strict-resume simulation
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/strict_resume_shadow_simulation.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/strict_resume_shadow_simulation.md
  - SHA-256: `93201c29de3acd9ac79f5012235667f10e8de818151015c76a795c129cd0a342`
- `data/reports/shadow_paper_resume_plan.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:09.067533+00:00`
  - Metric scope: staged resume plan; recommendations are not applied automatically
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_resume_plan.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_resume_plan.json
  - SHA-256: `397964e93e3a6afb71b4306455a733ab2fd11489a47a654fefe4154f7fedf4ac`
- `data/reports/shadow_paper_resume_plan.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable staged resume plan
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_resume_plan.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_resume_plan.md
  - SHA-256: `28aa6c3154a6e825cd5148308229d82de74b94b3261ff8120decec044ddb3f37`
- `data/reports/ta_forecast.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:07.903469+00:00`
  - Metric scope: latest deterministic TA forecast, not historical backtest evidence
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ta_forecast.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ta_forecast.json
  - SHA-256: `480a0865bd97ae74d6b0374f421c3d301c60f1f615af3e58c7c562052b603452`
- `data/reports/ta_summary.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:08.594139+00:00`
  - Metric scope: deterministic TA backtest summary over eligible historical rows and score thresholds
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ta_summary.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ta_summary.json
  - SHA-256: `57f7b53bb194c73f83d63f5f20251de24fc49bdf4740cca3eec1e6933874b45a`
- `data/reports/ta_backtest.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:08.594139+00:00`
  - Metric scope: deterministic TA backtest over eligible historical rows and score thresholds
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ta_backtest.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ta_backtest.json
  - SHA-256: `ad37520eabe2f8ace41856f4fd0aa0340416ceae18147e8ac0db80f1cf8ff695`
- `data/reports/ai_ta_performance.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:08.441177+00:00`
  - Metric scope: live AI TA call/shadow-candidate performance from decisions rows, not threshold replay
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ai_ta_performance.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ai_ta_performance.json
  - SHA-256: `0e41b07b97f6a738cf11df932cdf3a409ce564763fa03ee693e1aed15cd4b5d1`
- `data/reports/ai_ta_summary.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:08.772330+00:00`
  - Metric scope: AI TA deterministic replay summary; no AI calls are made during backtest
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ai_ta_summary.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ai_ta_summary.json
  - SHA-256: `8a6580d74daba73465bd76d283235b5881b117e77993311634e483bf25440dda`
- `data/reports/ai_ta_backtest.json`
  - Present: `True`
  - Generated at: `2026-05-15T06:35:08.772330+00:00`
  - Metric scope: AI TA deterministic replay of TA thresholds; ai_calls_made=0 by design
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ai_ta_backtest.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ai_ta_backtest.json
  - SHA-256: `59017d44ba8107b5d0574dd570e88a6e2848c6a92006e4c6680ef90639b456ed`
