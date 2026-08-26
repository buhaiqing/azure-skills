# RACI Matrix

Responsibility assignment for key CoE governance activities.

**Legend:**
- **R** — Responsible: performs the work
- **A** — Accountable: final decision authority
- **C** — Consulted: provides input before action
- **I** — Informed: notified after action

| Activity | Executive Sponsor | Platform Owner | AI Champion | On-call Engineer | Security |
|----------|:-----------------:|:--------------:|:-----------:|:----------------:|:--------:|
| Skill deployment approval | A | R | C | I | C |
| R2 operation approval | A | R | C | I | R |
| Alert response | I | A | R | R | I |
| Quarterly audit | A | R | C | I | C |
| Live canary maintenance | I | A | R | C | I |

## Role Definitions

| Role | Typical Owner |
|------|---------------|
| Executive Sponsor | VP/Director approving CoE budget and risk tolerance |
| Platform Owner | Engineer managing the Azure Skills infrastructure |
| AI Champion | Developer driving adoption and skill quality |
| On-call Engineer | SRE handling production incidents |
| Security | Security team reviewing access and data policies |

## Escalation Paths

- **R2 operation escalation:** AI Champion → Platform Owner → Executive Sponsor
- **Live canary failure:** On-call Engineer → AI Champion → Platform Owner
- **Security concern:** Any role → Security team directly
