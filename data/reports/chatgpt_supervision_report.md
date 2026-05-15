# Paper2Real ChatGPT Supervision Report

Snapshot ID: `e332aee20635dbc3`
Bundle generated at: `2026-05-15T16:00:24.129721+00:00`
Source commit SHA: `443bc6beb11a44cce93a923e0969de092ef8173a`

## Executive Verdict

**DO NOT RESUME Shadow Paper Test. Do not enable bonuses. Do not change trading logic.**

- Supervision verdict: `DO_NOT_RESUME_TRADING_OR_PAPER_TEST`
- Count consistency: `PASS`
- System health: `warning`
- Stale dataset warning: `True`
- Real trades executed: `1`
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

- `FAIL` System health is ok (daily_validation_report.json: system_health_status)
- `FAIL` Dataset is not stale (daily_validation_report.json: stale_dataset_warning)
- `PASS` Download ZIP is safe (daily_validation_report.json: download_zip_safe)
- `PASS` Secrets excluded (daily_validation_report.json: secrets_excluded)
- `FAIL` No real trades executed (daily_validation_report.json: trades_executed)
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

- `PASS` shadow_buy_count: `{"daily.shadow_buy_count": 217, "daily.shadow_buy_review_count": 217, "shadow_buy_failure_diagnosis.total_shadow_buy_records": 217, "shadow_buy_review.shadow_buy_count": 217, "shadow_paper_test.shadow_buy_review_count": 217, "strict_resume_shadow_simulation.total_shadow_buy_records": 217}`
- `PASS` risk_blocked_candidates: `{"daily.risk_blocked_candidates": 195, "risk_block_review.total_blocked_candidates": 195}`
- `PASS` smart_money_shadow_count: `{"daily.shadow_smart_money_count": 181, "smart_money_review.smart_money_shadow_count": 181}`

## Required Report Inventory

- `data/reports/daily_validation_report.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:24.120056+00:00`
  - Metric scope: canonical daily system health, endpoint, safety, learning, TA, and AI TA summary snapshot
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/daily_validation_report.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/daily_validation_report.json
  - SHA-256: `1fd24b0d21972da8e511dfde20b667af1ab7614e290bd3e579df3363315881c9`
- `data/reports/daily_validation_report.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable daily validation summary
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/daily_validation_report.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/daily_validation_report.md
  - SHA-256: `cdd01f53610c0277579078366d582ad1c560cd25688b2c3cac85649a2f972158`
- `data/reports/risk_block_review.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:20.819505+00:00`
  - Metric scope: risk-blocked candidate review from decisions.risk_blocked_candidate rows
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/risk_block_review.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/risk_block_review.json
  - SHA-256: `28a1adf41b7a3fa9e449e911995db3434ff4bbe59a39b922bf85b2c4db02c1bc`
- `data/reports/risk_block_review.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable risk-blocked candidate review
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/risk_block_review.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/risk_block_review.md
  - SHA-256: `33d766a001240fe1863dbe3aa83f2ba88abe3cd36788301dc9eae2aad33d272b`
- `data/reports/smart_money_review.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:20.747749+00:00`
  - Metric scope: Smart Money shadow evidence review; not an execution approval
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/smart_money_review.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/smart_money_review.json
  - SHA-256: `c3fcddd5312fc990e92e9ffb08edc5f771d217c9378b4f22bb2a8e26fe7d47b3`
- `data/reports/smart_money_review.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Smart Money shadow review
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/smart_money_review.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/smart_money_review.md
  - SHA-256: `f731426b591f49d7e2957859eb989d44dfed50fa01b3f74192842036e5b5da68`
- `data/reports/shadow_buy_review.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:22.021629+00:00`
  - Metric scope: Shadow BUY evidence review from decisions.shadow_action=BUY rows
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_review.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_review.json
  - SHA-256: `24146843b2973d723f916d83081482764d23880b98d0f14c08708896ce6db417`
- `data/reports/shadow_buy_review.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Shadow BUY review
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_review.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_review.md
  - SHA-256: `494e91498eff6dce766d2bcb855406574c2d48331937b14e724f09abefe7738f`
- `data/reports/shadow_paper_test_report.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:22.023503+00:00`
  - Metric scope: paper-only Shadow Paper Test lifecycle and paused-entry state
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_test_report.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_test_report.json
  - SHA-256: `6a44698ed01e5fc4448c19eb8c8361a0ef70d894da5aa9778f88949d71ec261d`
- `data/reports/shadow_paper_test_report.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Shadow Paper Test state
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_test_report.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_test_report.md
  - SHA-256: `94c84e1824f6b36e2056e92d4cee93be215de25e8afc369b6cc960ba61985670`
- `data/reports/shadow_buy_failure_diagnosis.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:22.177225+00:00`
  - Metric scope: read-only failure diagnosis across Shadow BUY records and paper trades
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_failure_diagnosis.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_failure_diagnosis.json
  - SHA-256: `01fcd251f9e50c7490b3e102bc9684e7001d941b1911c70228ce706902dd7c84`
- `data/reports/shadow_buy_failure_diagnosis.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable Shadow BUY failure diagnosis
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_buy_failure_diagnosis.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_buy_failure_diagnosis.md
  - SHA-256: `74ba431d818820d513cab381eccbcb81a2f01f83375fa3b7f41e5a3e1d08ef1f`
- `data/reports/strict_resume_shadow_simulation.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:22.310709+00:00`
  - Metric scope: read-only staged strict-resume simulation; no entries are enabled
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/strict_resume_shadow_simulation.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/strict_resume_shadow_simulation.json
  - SHA-256: `800eee36eccdac4f98ba7149104c964b9d3775f2e9793e025cd834367482ae8f`
- `data/reports/strict_resume_shadow_simulation.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable strict-resume simulation
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/strict_resume_shadow_simulation.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/strict_resume_shadow_simulation.md
  - SHA-256: `886ce4080a8d2a2bdae95d44375b4370bfdee75bd812aa64a58dda0f424ae3c8`
- `data/reports/shadow_paper_resume_plan.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:22.036400+00:00`
  - Metric scope: staged resume plan; recommendations are not applied automatically
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_resume_plan.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_resume_plan.json
  - SHA-256: `a26f08d8f795eb3ebeebb694bde8c4d969a635e3746a41039126658c2c9d1ab1`
- `data/reports/shadow_paper_resume_plan.md`
  - Present: `True`
  - Generated at: `None`
  - Metric scope: human-readable staged resume plan
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/shadow_paper_resume_plan.md
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/shadow_paper_resume_plan.md
  - SHA-256: `ce89237f3be68f996ed40cef0806ea756d481fb5fbc6a3050f615570df7e07b4`
- `data/reports/ta_forecast.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:21.426624+00:00`
  - Metric scope: latest deterministic TA forecast, not historical backtest evidence
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ta_forecast.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ta_forecast.json
  - SHA-256: `42025fbb5c46895bb06950c418b512b770e4944a37beaa772f6ec845411bf4c6`
- `data/reports/ta_summary.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:21.808142+00:00`
  - Metric scope: deterministic TA backtest summary over eligible historical rows and score thresholds
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ta_summary.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ta_summary.json
  - SHA-256: `f213a332adc0b8180592ffb8a111d9393b439b50efcd58ad3f36bcabafe1418b`
- `data/reports/ta_backtest.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:21.808142+00:00`
  - Metric scope: deterministic TA backtest over eligible historical rows and score thresholds
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ta_backtest.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ta_backtest.json
  - SHA-256: `256bd16e4b656d2d4a9b9ce8d628d997001a7fdbbef0762868e8eb588f0c0604`
- `data/reports/ai_ta_performance.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:21.711787+00:00`
  - Metric scope: live AI TA call/shadow-candidate performance from decisions rows, not threshold replay
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ai_ta_performance.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ai_ta_performance.json
  - SHA-256: `4e72542d412f64e3e76bd5b8d9d6e321c939042b055e778737595e45f5c02248`
- `data/reports/ai_ta_summary.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:21.940360+00:00`
  - Metric scope: AI TA deterministic replay summary; no AI calls are made during backtest
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ai_ta_summary.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ai_ta_summary.json
  - SHA-256: `046b5ee611173fc032f5b428bfbf84138a0e968afdf96da25a1a738d743f4030`
- `data/reports/ai_ta_backtest.json`
  - Present: `True`
  - Generated at: `2026-05-15T16:00:21.940360+00:00`
  - Metric scope: AI TA deterministic replay of TA thresholds; ai_calls_made=0 by design
  - Branch raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/shadow-paper-paused-20260513/data/reports/ai_ta_backtest.json
  - Commit-pinned raw URL: https://raw.githubusercontent.com/benyamin-persia/paper2real/443bc6beb11a44cce93a923e0969de092ef8173a/data/reports/ai_ta_backtest.json
  - SHA-256: `f36aaecf06e5372d3bc9a40674c5d463e70655e125a1db845f58a7d7b9deece3`
