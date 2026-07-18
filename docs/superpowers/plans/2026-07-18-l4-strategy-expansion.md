# L4 策略覆盖扩充计划 ✅ 已完成

> **目标**: 将 self-healing 策略从 6 个 skill 扩充到 16 个，达到 L4 覆盖门槛（50%）
> **最终 commit**: `d258b89`
> **实际**: 6 → 31 skill（100%），超越目标
> **范围**: 新增 10 个策略 JSON + registry 更新 + 6 个 SKILL.md 追加 L4 段落 + validate 验证
> **约束**: 每个策略 JSON 只写有把握的 operation；不写臆测的 API 字段

---

## 目标技能清单

| # | Skill | 优先级 | 非 risky 操作（计划写入） |
|---|-------|--------|--------------------------|
| 1 | `azure-vnet-ops` | P0 | vnet_create, subnet_create |
| 2 | `azure-dns-ops` | P0 | dns_zone_create, dns_record_set_create |
| 3 | `azure-postgres-ops` | P1 | postgres_create, server_start |
| 4 | `azure-redis-ops` | P1 | redis_create, redis_restart |
| 5 | `azure-monitor-ops` | P1 | alert_rule_create, action_group_create |
| 6 | `azure-cosmos-ops` | P2 | cosmosdb_create, database_create |
| 7 | `azure-acr-ops` | P2 | acr_create, acr_build |
| 8 | `azure-function-ops` | P2 | functionapp_create |
| 9 | `azure-storageaccount-ops` | P2 | storage_create |
| 10 | `azure-cosmos-ops` (扩展) | P2 | container_create, throughput_update |

**不在本次范围**（API 复杂或 destructive 为主）：`azure-site-recovery-ops`, `azure-eventhub-ops`, `azure-servicebus-ops`, `azure-backup-ops`

---

## 实施步骤

**每个 skill**：读取 SKILL.md → 确认 operation 名 → 写策略 JSON → 更新 registry.json → validate.py → 追加 SKILL.md L4 段落 → 全量测试

### 步骤 1: vnet-ops + dns-ops（基础设施，依赖最多）

```
Skill: azure-vnet-ops
vnet_create: provisioningState=Succeeded → heal: az network vnet wait
subnet_create: provisioningState=Succeeded → heal: az network vnet subnet wait

Skill: azure-dns-ops
dns_zone_create: provisioningState=Succeeded → heal: az network dns zone wait
```

### 步骤 2: postgres-ops + redis-ops（数据层）

### 步骤 3: monitor-ops + acr-ops

### 步骤 4: function-ops + cosmos-ops

### 步骤 5: storageaccount-ops

### 步骤 6: 全量验证 + commit

---

## 验收标准

- [ ] 新增 10 个策略 JSON 文件
- [ ] `validate.py` 报 16 个策略文件全部 valid
- [ ] 13/13 测试仍然 PASS
- [ ] 16 个 skill 的 SKILL.md 有 L4 段落
- [ ] registry.json version bump（1.1.0 → 1.2.0）
- [ ] Spec §2.3 模块清单更新
