---
title: 健康仪表板
description: health_dashboard.py 指标可视化
---

# 健康仪表板

> 查看 L4 闭环的健康状态和趋势。

## 1. CLI 使用

```bash
# 基本输出
python scripts/health_dashboard.py

# 指定报告路径
python scripts/health_dashboard.py --report my-report.json

# 显示 7 天趋势
python scripts/health_dashboard.py --trend-dir benchmark/

# 输出格式
python scripts/health_dashboard.py --format table  # 默认
python scripts/health_dashboard.py --format json

# 写入 Azure Monitor
python scripts/health_dashboard.py \
  --azure-monitor \
  --resource-id "/subscriptions/xxx/.../applicationinsights/xxx"
```

## 2. 输出示例

```
══════════════════════════════════════════════════
          Azure Skills L4 Health
══════════════════════════════════════════════════

L4 Certification Targets:
  ✓ Safety Pass Rate:         100%  ████████████████████ 100%
  ✓ Auto-Heal Success Rate:   93%  ███████████████████▌  93%
  ✓ Escalation Rate:            6%  ██▌                       6%

7-Day Trend:
  Day    Safety  Heal   Esc
  07-11   100%   95%    4%
  07-12   100%   91%    7%
  ...

Skill-by-Skill Health:
  ✓ azure-vm-ops           10/10  ████████████████████
  ✓ azure-aks-ops            8/10  ████████████████▌
  ⚠ azure-blobstorage-ops    9/10  ████████████████
```

## 3. Azure Monitor 指标

开启 `--azure-monitor` 后写入以下指标：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `l4_safety_pass_rate` | Gauge | 安全通过率 (0-100) |
| `l4_auto_heal_success_rate` | Gauge | 自愈成功率 (0-100) |
| `l4_escalation_rate` | Gauge | 人工介入率 (0-100) |
| `l4_scenarios_total` | Counter | 总场景数 |
| `l4_scenarios_passed` | Counter | 通过数 |
| `l4_scenarios_failed` | Counter | 失败数 |

## 4. 健康阈值

| 指标 | 目标值 | 告警阈值 | 严重程度 |
|------|--------|---------|---------|
| Safety Pass Rate | 100% | < 95% | Critical |
| Auto-Heal Success Rate | ≥ 85% | < 70% | Warning |
| Escalation Rate | ≤ 15% | > 25% | Warning |
