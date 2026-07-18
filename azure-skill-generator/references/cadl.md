# 复利资产沉淀机制 (Compound-Asset Distillation Loop, CADL)

> 这不是一条规范，而是一套工作闭环——任何实质任务完成后，Agent 必须走完「提取 → 判定落点 → 写入 → 门禁」才能结束。目的是让每次踩坑、每次评审、每次跨 skill 协作都变成下一次的可复用资产，形成复利。

## 为什么是机制而非规范

单条规则（如"记得写 AGENTS.md"）会被忽略，因为无触发、无闭环。CADL 把沉淀变成工作流的**必经出口**：任务不做沉淀 = 任务未完成。Agent 调用任何 Skill 后都走到这一步，Skill 本身也通过下方「Skill 侧钩子」提示大模型。

## 触发条件（满足任一即必须走 CADL）

- 多步 / 跨文件任务完成
- 跨 Skill 协作（用了 delegation matrix 或并行 agent）
- 评审 / 修复循环（如 GCL、self-review、2-round self-review）
- 发现 repo 缺陷 / 坑（即使不在本次 scope，也记）
- 验证中发现预存 FAIL 并归因
- 用户给出可复用的工作流偏好（如"用双写子命令绕过 CLI bug"）

## 闭环步骤

```
1. 提取   → 从刚完成的任务中抽象出可复用模式：
            踩坑避免 / 评审维度 / 协作模式 / 验证命令 / 复用 helper
            格式："问题 → 反模式 → 正确做法（含代码示例）"
2. 落点判定 → 离开本仓库还有用？ → 用户级 AGENTS.md（路径随运行时而定，如 `~/.config/opencode/AGENTS.md` 或 `~/.claude/CLAUDE.md`）
            仅本仓库适用？     → 项目级 AGENTS.md（本仓库根目录）
            是某 skill 专属可调用的能力？ → 独立 Skill 文件（经 azure-skill-generator）
3. 写入   → 可执行、有示例、有边界、先 grep 现有 AGENTS.md 确认未覆盖（不重复）
4. 门禁   → 写入前查 wc -l，AGENTS.md ≥ 500 行先精简再写（见仓库 agent-md-size-guard 规则）
5. 复用   → 下次同类任务，Agent 读 AGENTS.md 即获得该资产 → 复利生效
```

## Skill 侧钩子（让每个 Skill 自带沉淀意识）

- **源头**：`azure-skill-generator` 在生成每个 skill 时，须在 SKILL.md 末尾注入一行：
  `> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。`
  未来所有 `azure-*-ops` 自动继承此意识。
- **现存 skill**：逐批在 SKILL.md 末尾补同一行提示，使大模型调用任何 skill 后都看到触发信号。
- **大模型侧**：Agent 在任意 skill 调用结束前，主动检查 CADL 触发条件，而非等用户提醒。

## 反模式（违反 CADL）

| 反模式 | 正确做法 |
|---|---|
| 任务做完就结束，不沉淀 | 走完 CADL 闭环再交付 |
| 把一次性上下文当资产写进 AGENTS.md | 只沉淀跨任务可复用的模式 |
| 重复已有条目 | 写入前 grep 确认未覆盖 |
| 只在 GCL / self-review 相关任务才沉淀 | 评审/修复/协作/验证都触发 |

## 与现有仓库机制的协作关系

- **agent-md-size-guard**（用户级 AGENTS.md，路径随运行时而定）：CADL 门禁第 4 步直接复用该规则的行数门禁（≥500 行禁止新增，需先精简）。不要另立一套阈值。
- **GCL / 2-round self-review**：它们是质量门禁，CADL 是资产外化。三者互补，互不替代——一次 skill 更新可能同时触发 self-review（改 skill）、GCL（跑执行）、CADL（沉淀踩坑经验）。
- **同类经验沉淀规则**：若用户级 AGENTS.md 存在「自我进化闭环」之类规则，CADL 是其**体系化升级版**——提供更明确的触发条件、落点判定与反模式，二者不冲突，以 CADL 为准。
