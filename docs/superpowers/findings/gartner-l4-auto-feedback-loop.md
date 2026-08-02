# CADL Finding — Gartner L4 自动化闭环

> 来源：`feature/gartner-l4-auto-feedback-loop` 分支实现，2026-07-18

## Pattern
L4 自动化闭环 = `observe` (ARM API) + `diff` (desired vs actual) + `heal` (策略 JSON) + `escalate` (升人工).

## Anti-Pattern
不要在 `auto_feedback_loop.py` 中硬编码修复策略；每新增一个 skill 都要改代码。

## 正确做法
策略外置到 `scripts/self_healing/<skill>_heal.json`，`loader.py` 读取注册表；新增 skill 只需加 JSON。

## 范围
本仓库 (azure-skills).
