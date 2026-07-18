#!/usr/bin/env python3
"""
escalation.py — 升人工：构造诊断上下文，返回人类可读消息

不抛异常，不写文件（trace 由调用方负责）。
"""
from dataclasses import dataclass


@dataclass
class EscalationContext:
    skill: str
    operation: str
    command: str
    exit_code: int
    error: str
    heal_attempts: int
    trace_id: str


def escalate(ctx: EscalationContext) -> str:
    """
    返回人类可读升人工消息，包含诊断上下文和建议操作。
    """
    lines = [
        f"⚠️  **需要人工介入** — {ctx.skill} / {ctx.operation}",
        "",
        f"命令: `{ctx.command}`",
        f"退出码: `{ctx.exit_code}`",
        f"错误: {ctx.error}",
        f"补偿尝试: {ctx.heal_attempts} 次（已达上限）",
        f"Trace ID: `{ctx.trace_id}`",
        "",
        "**建议操作:**",
        "1. 登录 Azure Portal 检查资源当前状态",
        "2. 查看 Activity Log:",
        "   `az monitor activity-log list --resource-group <rg> --resource <name>`",
        "3. 确认配额: `az vm list-usage --location <loc>`",
        "4. 确认 RBAC 权限: `az role assignment list --assignee <sp>`",
        "5. 修复后，附 Trace ID 重新提交任务",
    ]
    return "\n".join(lines)
