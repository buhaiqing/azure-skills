# Communication Template

## Internal Announcement Template

---

**Subject:** [CoE] Azure Skills Platform — Live for {Team Name}

We are excited to announce that the Azure Skills **Center of Excellence (CoE)** is now live for **{Team Name}**.

### What is changing

The CoE provides a governed harness for running AI agents against your Azure resources. All agent executions are subject to:

- **Safety guardrails** — live canary checks before and after every execution
- **Risk tier enforcement** — elevated-risk operations require explicit approval
- **Audit trail** — every action is logged and attributable

### What you need to do

1. Review the **Agent Usage Policy** below
2. Complete the Week One Checklist (linked from the CoE README)
3. Attend the Runbook walkthrough — schedule with your AI Champion

### Key contacts

| Role | Contact |
|------|---------|
| AI Champion | `{ai_champion_email}` |
| Platform Owner | `{platform_owner_email}` |
| On-call | `{oncall_email}` |

---

## Agent Usage Policy

### What agents CAN do

| Capability | Example |
|-----------|---------|
| Read Azure resource metadata | `az resource show --ids <id>` |
| Query logs via read-only APIs | Read logs, metrics, diagnostics |
| Suggest code changes | Present diff for human review |
| Execute pre-approved low-risk operations | Stop/start VMs in non-production, read config |

### What agents CANNOT do

| Prohibition | Reason |
|-------------|--------|
| Delete Azure resources without dual approval | Data loss risk |
| Modify security or IAM configurations | Privilege escalation risk |
| Access production secrets or keyvault directly | Credential exposure |
| Execute scripts without governance canary passing | Uncontrolled side effects |

### Pre-execution requirements

Before any agent runs against a live environment:

1. **Safety gate** — `live_canary.py` must pass all checks for the target scope
2. **Risk tier check** — if the operation is `HIGH` or `CRITICAL` risk, an approved ticket must exist in the change management system
3. **Human in the loop** — for R2 (elevated risk) operations, a second engineer must acknowledge

### Incident response

If an agent produces unexpected behavior:

1. **Immediately revoke** the agent session
2. **File an incident ticket** with the `ai-incident` label
3. **Notify** the AI Champion and Platform Owner via the escalation webhook
4. **Preserve logs** — do not clear agent output before the post-mortem

### Questions

Reach out to your AI Champion or open a ticket with the `coe-support` label.
