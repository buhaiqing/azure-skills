# Token Efficiency Requirements (P0 — 强制)

> 在保持 Agent 可执行性的前提下，最小化每个 Skill 的 Token 消耗。

## 规则表格

| 规则 | 要点 | 节省 |
|------|------|------|
| **TE-1** API 查询 > 静态表格 | 用 `az` 命令获取版本/配额，不硬编码 | ~200-500/文件 |
| **TE-2** 省略不必要的 docstring | Markdown 用 `#` 注释代替函数级说明 | ~100-200/文件 |
| **TE-3** 紧凑错误表 | 每行 1 个错误码，≤3 列 | ~300-500/文件 |
| **TE-4** JSON paths 集中声明 | 文件顶部统一声明，不重复 | ~50-100/文件 |
| **TE-5** YAML anchors | `example-config.yaml` 用 `&anchor` 消除重复 | ~200-400/文件 |
| **TE-6** 消除跨文件重复 | SKILL.md 已有完整流程，references 不重复 | 因 Skill 而异 |
| **TE-7** 专业内容分层 | AIOps/FinOps 等深度分析放 `references/`；安全敏感操作单独标注并要求显式确认 | ~3,000-8,000/文件 |

## 自检清单

### Round 1, Item 4 — Token Efficiency (P0 — 强制)

**必检项**：TE-1~TE-7 是否全部满足？未满足则 **BLOCK**。

| TE 规则 | 检查方法 | 不通过则 |
|---------|---------|---------|
| **TE-1** API 查询 > 静态表格 | 用 `az [service] show/list` 获取版本/配额，不硬编码 | 替换为 `az` 查询命令 |
| **TE-2** 省略不必要的 docstring | Markdown 说明精简，保留核心逻辑 | 删除 docstring，改用简洁描述 |
| **TE-3** 紧凑错误表 | 每行 1 个错误码，≤3 列 | 合并列，每行 1 个错误码 |
| **TE-4** JSON paths 集中声明 | 文件顶部统一声明，不重复 | 移至文件顶部统一声明 |
| **TE-5** YAML anchors | `example-config.yaml` 用 `&anchor` 消除重复 | 用 YAML anchors 消除 |
| **TE-6** 消除跨文件重复 | SKILL.md 已有完整流程，references 不重复 | 删除 references 中的重复 |
| **TE-7** 专业内容分层 | AIOps/FinOps 等深度分析放 `references/`；安全敏感操作单独标注并要求显式确认 | 移至 `references/` + 添加 Security-Sensitive 标注 |

**发现任一违规 → 立即修复 → 重新检查直到全部通过。**

## 不可压缩的内容

Agent 可执行命令本身（参数、JSON paths）、错误恢复逻辑、安全门、Credential 规则、跨技能编排链。

## 内容去重要求

内容去重是 Token Efficiency 的子集，强制执行：

1. **SKILL.md ↔ references/**：SKILL.md 是入口点（entry point），只包含触发条件、操作流程摘要；references/ 提供深度，**禁止重复**。
2. **references/ 内部**：同一错误码/概念只在一处定义，使用 `{{output.*}}` 引用。
3. **跨 Skill 引用**：当一个 Skill 需要另一个 Skill 的能力时，使用 `## Delegation` 段落引用，而非内联复制。
4. **检查方法**：
   - 搜索 SKILL.md 中的完整操作步骤 → 确认已移至 references/
   - 搜索重复的错误码描述行 → 合并或使用锚点引用

**违规处理**：发现内容重复 → 立即重构 → 重新检查直到零重复。
