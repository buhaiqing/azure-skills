---
title: 编排引擎
description: orchestrator.py 跨服务依赖诊断
---

# 编排引擎

> 当一个问题涉及多个 Azure 服务时，自动分析依赖链并生成修复顺序。

## 1. 依赖图

```
31 个节点，120+ 条边

示例：
┌─────────────┐
│  azure-aks │
└──────┬──────┘
       ├──▶ azure-vm-ops
       ├──▶ azure-vnet-ops
       ├──▶ azure-nsg-ops
       ├──▶ azure-lb-ops
       └──▶ azure-acr-ops
```

## 2. CLI 命令

### 列出依赖

```bash
python scripts/orchestrator.py --list-deps azure-aks-ops

# 输出：
# azure-aks-ops 直接依赖：
#   • azure-vm-ops (节点)
#   • azure-vnet-ops (网络)
#   • azure-nsg-ops (安全规则)
#   • azure-lb-ops (负载均衡)
```

### 诊断症状

```bash
python scripts/orchestrator.py --diagnose "AKS node not ready"

# 输出：
# 诊断：AKS node not ready
# ─────────────────────────────────────
# 依赖链 (BFS):
#   [L0] azure-aks-ops
#   [L1] azure-vm-ops → azure-vnet-ops → azure-nsg-ops
#
# 建议检查顺序：
#   1. azure-vm-ops: 检查节点状态
#   2. azure-nsg-ops: 检查 NSG 规则
#   3. azure-vnet-ops: 检查子网配置
```

### 生成修复计划

```bash
python scripts/orchestrator.py --heal azure-aks-ops "node_pool_expansion_failed"

# 输出：
# 修复计划：node_pool_expansion_failed
# ─────────────────────────────────────
# 拓扑顺序（reverse BFS）：
#   Step 1: azure-nsg-ops (先修依赖)
#   Step 2: azure-vnet-ops
#   Step 3: azure-vm-ops
#   Step 4: azure-aks-ops (最后修复目标)
```

### 列出 RCA 路径

```bash
python scripts/orchestrator.py --list-rca
```

### 查看沉淀模式

```bash
python scripts/orchestrator.py --list-patterns
```

## 3. Python API

```python
from orchestrator import Orchestrator

orch = Orchestrator()

# 获取依赖链
deps = orch.get_dependency_chain("azure-aks-ops")
print(deps)
# {'direct': ['azure-vm-ops', 'azure-vnet-ops', ...], 'transitive': [...]}

# 诊断症状
diag = orch.diagnose("AKS node not ready")
print(diag)
# {'symptom': '...', 'chain': [...], 'rca_paths': [...]}

# 生成修复顺序
heal_order = orch.healing_order("azure-aks-ops")
print(heal_order)
# ['azure-nsg-ops', 'azure-vnet-ops', 'azure-vm-ops', 'azure-aks-ops']

# 匹配 RCA 路径
rca = orch.match_rca_path("AKS node not ready")
print(rca)
# {'path': 'AKS → VM → NSG → VNet', 'confidence': 0.85}
```

## 4. BFS 遍历

```
症状：AKS 节点异常

BFS 遍历：
Level 0: AKS (症状节点)
Level 1: AKS ──▶ VM, VNet, NSG, LB (直接依赖)
Level 2: VM ──▶ NSG, VNet (依赖的依赖)
Level 3: ...

诊断顺序：
1. 检查 AKS 本身状态
2. 检查 AKS 的依赖（VM, VNet, NSG, LB）
3. 检查依赖的依赖
```

## 5. 修复顺序

`healing_order()` 按 BFS reverse order 返回：

```
先修复叶子节点，再修复根节点

例如：NSG → VM → AKS
  1. 先修复 NSG（叶子，最底层依赖）
  2. 再修复 VM（中间层）
  3. 最后修复 AKS（根，目标服务）
```

## 6. CADL 沉淀

跨服务诊断模式自动写入 `.runtime/cross_skill_patterns/`：

```bash
ls .runtime/cross_skill_patterns/
# aks_vm_nsg_loop.jsonl
# vm_lb_healthcheck.jsonl
```

每行 JSONL 格式：

```jsonl
{"pattern": "aks_vm_nsg_loop", "frequency": 5, "skills": ["azure-aks-ops", "azure-vm-ops", "azure-nsg-ops"]}
```
