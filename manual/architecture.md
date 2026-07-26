---
title: 系统架构
description: azure-skills L4 自动化闭环架构设计
---

# 系统架构

## 1. 整体架构

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              Azure Skills L4 架构                               │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                     │
│  │   User /   │────▶│  Decision   │────▶│   Execute   │                     │
│  │   Agent    │     │   Engine    │     │   Layer     │                     │
│  └─────────────┘     └─────────────┘     └─────────────┘                     │
│         │                  │                   │                                │
│         │                  ▼                   ▼                                │
│         │           ┌─────────────┐     ┌─────────────┐                     │
│         │           │   LLM       │     │   Azure    │                     │
│         │           │   Critic    │     │   CLI/API   │                     │
│         │           └─────────────┘     └─────────────┘                     │
│         │                  │                   │                                │
│         └──────────────────┴───────────────────┘                                │
│                                              │                                    │
│                                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐                  │
│  │                    Observe Layer                           │                  │
│  │              (ARM API / Azure Monitor)                   │                  │
│  └─────────────────────────────────────────────────────────┘                  │
│                                              │                                    │
│                                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐                  │
│  │                     Diff Engine                            │                  │
│  │           (desired_state vs actual_state)                 │                  │
│  └─────────────────────────────────────────────────────────┘                  │
│                                              │                                    │
│              ┌─────────────────────────────┴─────────────────────┐          │
│              ▼                                                       ▼          │
│  ┌─────────────────────────┐                           ┌─────────────────┐ │
│  │         Heal            │                           │    Escalate     │ │
│  │       (自愈)             │                           │    (升人工)      │ │
│  └─────────────────────────┘                           └─────────────────┘ │
│              │                                                       │          │
│              └───────────────────────┬───────────────────────────────┘          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐                  │
│  │                    Memory Layer                            │                  │
│  │         (skill, symptom, strategy → 成功率)              │                  │
│  └─────────────────────────────────────────────────────────┘                  │
│                                      │                                           │
│                                      ▼                                           │
│  ┌─────────────────────────────────────────────────────────┐                  │
│  │                   CADL 沉淀                               │                  │
│  │              (cross_skill_patterns)                      │                  │
│  └─────────────────────────────────────────────────────────┘                  │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 2. 核心组件

| 组件 | 文件 | 职责 | 输入 | 输出 |
|------|------|------|------|------|
| **Decision Engine** | `gcl_runner.py` | 判断执行路径 | 用户请求 | GCL 评分 |
| **Execute Layer** | `auto_feedback_loop.py` | 执行 az 命令 | command + desired_state | FeedbackResult |
| **LLM Critic** | `llm_critic.py` | 语义级审核 | generator_output + rubric | scores |
| **Orchestrator** | `orchestrator.py` | 跨服务依赖分析 | symptom | dependency_chain |
| **Memory Store** | `memory_store.py` | 经验持久化 | (skill, symptom, strategy) | recommend() |
| **Health Dashboard** | `health_dashboard.py` | 指标可视化 | l4-health-report.json | stdout |

## 3. 数据流

```
User Request
     │
     ▼
┌─────────────────────────────────────────┐
│          gcl_runner.py (GCL)           │
│  1. Generator: 生成 az 命令             │
│  2. Critic: 质量评分                   │
│  3. Loop: 迭代直到 PASS               │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│     auto_feedback_loop.py (L4)          │
│  1. Execute: 运行 az 命令              │
│  2. Observe: 查询资源状态              │
│  3. Diff: 对比 desired vs actual       │
│  4. Heal/Escalate: 修复或升人工       │
└─────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────┐
│          Memory + CADL                  │
│  1. record(): 记录执行结果            │
│  2. recommend(): 推荐最优策略          │
│  3. persist(): 沉淀跨服务模式          │
└─────────────────────────────────────────┘
```

## 4. L4 闭环流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      L4 闭环流程                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   Execute ──▶ Observe ──▶ Diff ──┬──▶ Heal ──▶ Done         │
│                                     │                            │
│                                     │ No Match                   │
│                                     ▼                            │
│                              Escalate ──▶ Human ──▶ Resume       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**详细步骤**：

1. **Execute** - 运行 az 命令
2. **Observe** - 调用 Azure API 获取资源状态
3. **Diff** - 对比 desired_state 和 actual_state
4. **Heal** - 如果不匹配，触发补偿策略
5. **Loop** - 重复直到状态匹配或达到最大修复次数
6. **Escalate** - 无法自愈时生成升人工报告

## 5. 依赖图结构

```
31 个 Azure 服务节点，120+ 条依赖边

示例依赖链：
┌─────────────┐
│  azure-aks │
└──────┬──────┘
       │
       ├──▶ azure-vm-ops (节点)
       ├──▶ azure-vnet-ops (网络)
       ├──▶ azure-nsg-ops (安全规则)
       ├──▶ azure-lb-ops (负载均衡)
       └──▶ azure-acr-ops (镜像仓库)

┌─────────────┐
│ azure-vm-ops │
└──────┬──────┘
       │
       ├──▶ azure-nsg-ops
       └──▶ azure-vnet-ops
```

## 6. 目录结构

```
azure-skills/
├── scripts/
│   ├── auto_feedback_loop.py      # L4 闭环核心
│   ├── gcl_runner.py              # GCL 评分
│   ├── llm_critic.py              # LLM Critic
│   ├── orchestrator.py            # 跨服务编排
│   ├── health_dashboard.py       # 仪表板
│   ├── memory/
│   │   └── memory_store.py       # 记忆层
│   ├── self_healing/
│   │   ├── cost_heal.json        # 成本自愈
│   │   └── *.json                # 其他策略
│   ├── dependency_graph.json     # 依赖图
│   └── mock_azure_scenarios/    # Mock 场景
├── tests/
│   ├── test_orchestrator.py
│   ├── test_llm_critic.py
│   └── test_memory_store.py
└── manual/
    └── *.md                       # 文档
```

## 7. Gartner L4 标准对照

| Gartner L4 特征 | azure-skills 实现 |
|-----------------|------------------|
| **Observe** | `Observe Layer` - ARM API 查询 |
| **Diff** | `Diff Engine` - desired vs actual |
| **Heal** | `Healing Rules` - 自动补偿 |
| **Escalate** | `Escalate` - 升人工 |
| **Memory** | `Memory Store` - 经验复用 |
| **Traceability** | `audit-results/` - 执行轨迹 |

## 8. 设计原则

1. **零外部依赖** - 核心逻辑使用 stdlib
2. **幂等性** - 重复执行不会产生副作用
3. **可观测性** - 完整的 trace 和 metrics
4. **记忆复用** - 历史经验指导未来决策
5. **安全第一** - destructive 操作必须人工确认
