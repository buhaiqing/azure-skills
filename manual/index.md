---
title: Azure Skills 文档中心
description: azure-skills L4 自动化闭环完整文档
---

# Azure Skills 文档中心

> 面向 AI Agent 开发者和 DevOps 工程师，支持 **31 个 Azure 服务**的 L4 自动化闭环。

## 📚 文档结构

```
manual/
├── index.md                 # 文档中心（本文）
├── user-guide.md           # 端到端用户指南（MS L400）
├── quick-start.md          # 5 分钟快速入门
├── architecture.md         # 系统架构设计
├── l4闭环.md               # L4 自动化闭环
├── llm-critic.md          # LLM 质量审核
├── orchestrator.md         # 跨服务编排
├── memory.md               # 执行记忆层
├── dashboard.md            # 健康仪表板
├── mock.md                 # Mock 验证
├── configuration.md        # 环境变量配置
├── troubleshooting.md       # 故障排查
├── best-practices.md       # 最佳实践
├── api-reference.md        # API 参考
├── extension.md            # 扩展指南
├── governance-federation.md # 联邦治理 / 风险分级
├── human-agent-ops-playbook.md # 人机协作运维
└── adoption-tiers.md       # sandbox → enterprise 采纳
```

## 🚀 快速链接

| 场景 | 文档 | 关键命令 |
|------|------|----------|
| 完整路径（推荐） | [用户指南](./user-guide.md) | `python scripts/live_canary.py --dry-run` |
| 第一次使用 | [快速入门](./quick-start.md) | `python scripts/auto_feedback_loop.py --skill azure-vm-ops ...` |
| 理解架构 | [系统架构](./architecture.md) | — |
| 自动修复 | [L4 闭环](./l4闭环.md) | `--desired-state '{"powerState": "VM running"}'` |
| 质量审核 | [LLM Critic](./llm-critic.md) | `--critic llm` |
| 跨服务问题 | [编排引擎](./orchestrator.md) | `--diagnose "AKS node not ready"` |
| 经验复用 | [记忆层](./memory.md) | `store.recommend()` |
| 查看健康 | [仪表板](./dashboard.md) | `python scripts/health_dashboard.py` |
| 人机协作 | [Ops Playbook](./human-agent-ops-playbook.md) | `risk_tiers.py --skill ...` |
| 组织采纳 | [采纳分级](./adoption-tiers.md) | sandbox → enterprise |
| 本地测试 | [Mock 验证](./mock.md) | `python scripts/run_all_scenarios.py` |
| 配置环境 | [环境配置](./configuration.md) | `cp .env.example .env` |

## 📊 核心能力矩阵

| 能力 | 组件 | 自动化程度 | 适用场景 |
|------|------|-----------|---------|
| L4 闭环 | `auto_feedback_loop.py` | 全自动 | 资源创建/修改 |
| LLM 审核 | `llm_critic.py` | 半自动 | 质量评分 |
| 跨服务诊断 | `orchestrator.py` | 全自动 | 依赖链分析 |
| 执行记忆 | `memory_store.py` | 全自动 | 策略推荐 |
| 健康仪表板 | `health_dashboard.py` | 只读 | 状态监控 |
| Mock 测试 | `mock_azure.py` | 全自动 | 离线验证 |

## 🔧 决策树

```
需要执行 Azure 操作？
     │
     ├── destructive (delete/stop)？
     │      YES → SKILL.md Safety Gate（必须人工确认）
     │      NO  ↓
     │
     ├── 有 desired_state？
     │      YES → auto_feedback_loop.py（自动校验+修复）
     │      NO  ↓
     │
     ├── 需要质量评分？
     │      YES → gcl_runner.py（+ llm_critic 可选）
     │      NO  ↓
     │
     └── 直接执行 az 命令
```

## 📈 L4 认证指标

| 指标 | 目标 | 当前 | 状态 |
|------|------|------|------|
| 安全通过率 | 100% | 100% | ✅ |
| 自愈成功率 | ≥ 85% | 93% | ✅ |
| 人工介入率 | ≤ 15% | 6% | ✅ |
| CADL 沉淀 | 100% | 94% | ✅ |

> 查看完整认证报告：[l4-certification-2026-07-27.md](../docs/superpowers/reports/l4-certification-2026-07-27.md)

## 🎯 常见任务

### 创建 VM 并自动等待就绪

```bash
python scripts/auto_feedback_loop.py \
  --skill azure-vm-ops \
  --operation vm_create \
  --command "az vm create --name my-vm --resource-group my-rg --image UbuntuLTS" \
  --desired-state '{"powerState": "VM running"}'
```

### 诊断 AKS 问题

```bash
python scripts/orchestrator.py --diagnose "AKS node not ready"
```

### 使用 LLM 评分

```bash
export DASHSCOPE_API_KEY=sk-xxx
python scripts/gcl_runner.py --skill azure-vm-ops --critic llm --request "az vm list"
```

### 查看健康状态

```bash
python scripts/health_dashboard.py
```

## 🔗 相关链接

- [L4 达成报告](../docs/superpowers/reports/l4-achievement-2026-07-27.md)
- [开发路线图](../docs/superpowers/plans/2026-07-26-L3.5-to-L4-roadmap.md)
- [GitHub 仓库](https://github.com/buhaiqing/azure-skills)
- [问题反馈](https://github.com/buhaiqing/azure-skills/issues)

## 📝 文档版本

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-07-27 | 初始版本，L4 达成 |
