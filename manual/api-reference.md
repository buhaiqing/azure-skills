---
title: API 参考
description: 所有核心函数的完整 API 签名
---

# API 参考

## 1. auto_feedback_loop.py

### run_with_feedback

```python
def run_with_feedback(
    skill: str,
    operation: str,
    command: str,
    desired_state: dict,
    risky: bool = False,
    max_heal_attempts: int = 2,
    trace_id: str | None = None,
    dry_run: bool = False,
    observe_cost: bool = False,
) -> FeedbackResult
```

**Args**:
- `skill`: 技能名称
- `operation`: 操作名称
- `command`: az 命令
- `desired_state`: 期望状态
- `risky`: 跳过危险操作确认
- `max_heal_attempts`: 最大修复次数
- `trace_id`: Trace ID
- `dry_run`: 仅演练
- `observe_cost`: 开启成本观测

**Returns**: `FeedbackResult`

---

## 2. llm_critic.py

### CriticModel

```python
class CriticModel:
    def __init__(
        self,
        provider: str = "auto",
        model_name: str | None = None,
        temperature: float = 0.1,
        timeout: int = 30,
    )

    def score(
        self,
        generator_output: dict,
        rubric: dict,
        trace: dict,
        max_iter: int = 3,
    ) -> dict

    def benchmark(self, n_runs: int = 5) -> dict
```

---

## 3. orchestrator.py

### Orchestrator

```python
class Orchestrator:
    def __init__(self, dependency_graph_path: str = "scripts/dependency_graph.json")

    def get_dependency_chain(self, skill: str, depth: int = 3) -> dict

    def diagnose(self, symptom: str, max_depth: int = 3) -> dict

    def healing_order(self, skill: str) -> list[str]

    def match_rca_path(self, symptom: str) -> dict

    def persist_pattern(self, pattern: dict) -> str
```

---

## 4. memory_store.py

### MemoryStore

```python
class MemoryStore:
    def __init__(self, storage_dir: str = ".runtime/memory/")

    def record(
        self,
        skill: str,
        symptom: str,
        strategy: str,
        success: bool,
        duration_seconds: float = 0.0,
        metadata: dict | None = None,
    ) -> str

    def recommend(
        self,
        skill: str,
        symptom: str,
        top_k: int = 1,
    ) -> list[dict]

    def transfer(
        self,
        from_skill: str,
        to_skill: str,
        symptom_mapping: dict[str, str],
        min_success_rate: float = 0.0,
    ) -> int

    def prune(
        self,
        max_age_days: int = 30,
        min_success_rate: float = 0.5,
    ) -> int

    def stats(self) -> dict
```

---

## 5. FeedbackResult

```python
@dataclass
class FeedbackResult:
    status: str           # "success" | "healed" | "escalated" | "failed"
    actual_state: dict  # Azure API 返回的原始状态
    heal_attempts: int  # 实际修复尝试次数
    trace_id: str       # 关联 trace ID
    message: str          # 人类可读摘要
    escalation: str|None # 升人工消息
```

---

## 6. 返回值说明

### status 值

| 值 | 含义 | 动作 |
|---|---|---|
| `success` | 成功，状态匹配 | 无需操作 |
| `healed` | 自动修复成功 | 检查结果 |
| `escalated` | 修复失败，已升人工 | 查看 escalation 消息 |
| `failed` | 命令执行失败 | 修复命令后重试 |
