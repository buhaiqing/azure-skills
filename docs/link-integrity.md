# 文档链接关联检测

> 确保 Skill 文档中的链接有效，引用关系一致。

## Link Integrity Rules

| 规则 | 描述 | 检查方法 |
|------|------|---------|
| **LI-1** 内部链接有效 | 所有 `[text](../references/...)` 和 `[text](./references/...)` 链接指向存在的文件 | 扫描所有 `.md` 文件的正则 `\[.*\]\(\.*references/.*\.md\)` |
| **LI-2** 外部链接有效 | Azure 文档链接 (`docs.microsoft.com`, `learn.microsoft.com`) 格式正确（URL 不含占位符） | 扫描所有外部链接，确认无 `{{` 残留 |
| **LI-3** 锚点存在 | `{#anchor-name}` 定义后，文中必须有 `[text](#anchor-name)` 引用 | 扫描 `{#` 定义和 `#anchor-name` 引用 |
| **LI-4** 跨 Skill 引用一致 | `Delegation` 段落引用的其他 Skill 必须存在于仓库中 | 检查所有 `[skill-name]` 引用对应的目录是否存在 |

## 检查流程

在 **每次提交前** 执行：

```bash
# 1. 检查内部链接
grep -rn '\]\(.*references/.*\.md\)' --include="*.md" .

# 2. 检查外部链接不含占位符
grep -rn '{{' --include="*.md" . | grep -v '{{env' | grep -v '{{user' | grep -v '{{output'

# 3. 检查锚点定义与引用
grep -rn '{#' --include="*.md" .  # 收集所有锚点
grep -rn '\[.*\](#.*\)' --include="*.md" .  # 验证引用

# 4. 检查跨 Skill 引用
grep -rn 'azure-.*-ops' --include="*.md" . | grep -v '\./azure-'  # 非目录引用需确认存在
```

## 常见问题修复

| 问题 | 修复方式 |
|------|---------|
| 链接文件不存在 | 删除链接或创建空占位文件（如果 Skill 尚未实现） |
| 外部链接含 `{{` | 展开 placeholder 为实际值，或改用 `{{env.*}}` / `{{user.*}}` |
| 孤立的锚点定义 | 删除 `{#anchor}` 或补全引用 |
| 跨 Skill 引用目录不存在 | 更新引用为 "TODO: delegate to future `azure-xxx-ops`" 或创建委托段落 |

## 自动化工具（可选）

如需自动化检查，可添加 `scripts/link-checker.py`（非强制，不影响 Skill 可执行性）：

```python
#!/usr/bin/env python3
"""检查 Skill 文档中的链接完整性"""
import re
import sys
from pathlib import Path

def check_links(repo_root: Path) -> list[str]:
    issues = []
    for md in repo_root.rglob("*.md"):
        content = md.read_text()
        # LI-1: 内部引用 .md 文件
        internal_links = re.findall(r'\[.*?\]\((.*?\.md)\)', content)
        for link in internal_links:
            if not (md.parent / link).exists():
                issues.append(f"{md}: broken internal link: {link}")
        # LI-2: 外部链接含占位符
        if '{{' in content and '{{env' not in content and '{{user' not in content and '{{output' not in content:
            issues.append(f"{md}: placeholder in external link")
    return issues

if __name__ == "__main__":
    issues = check_links(Path(__file__).parent.parent)
    if issues:
        print("Link issues found:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    print("All links OK")
```
