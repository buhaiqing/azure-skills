# Weekly Evaluation Report

> Generated: 2026-07-31T16:39:18.639137+00:00

## Mock scenario suite

Exit: 0

```
总场景数: 93
通过: 93
失败: 0
通过率: 100.0%
报告已生成: /Users/bohaiqing/opensource/git/azure-skills/benchmark/l4-verify-2026-Q3.md
```

## Metrics collector

Exit: 0

```json
{
  "safety_pass_rate": {
    "target": 100,
    "actual": 100.0,
    "met": true
  },
  "auto_heal_success_rate": {
    "target": 85,
    "actual": 100.0,
    "met": true
  },
  "escalation_rate": {
    "target": 15,
    "actual": 0.0,
    "met": true
  }
}
```

## Live canary (dry-run)

Exit: 0

```
mode=dry_run total=8 passed=8 failed=0 skipped=0
report: /Users/bohaiqing/opensource/git/azure-skills/benchmark/l4-live-canary-20260731.md
```

## LLM Critic

Skipped (`--with-critic` not set). Fallback: `gcl_runner.py --critic rule`.
