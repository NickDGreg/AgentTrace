# DESIGN

AgentTrace design priorities:
- deterministic benchmark behavior over realism depth
- task definitions as data, not implementation code
- black-box evaluation of external agents
- small, typed, inspectable harness modules

Start here:
- high-level architecture: `ARCHITECTURE.md`
- design principles: `docs/design-docs/core-beliefs.md`
- codemap entrypoint: `docs/design-docs/index.md`

Any structural change should be accompanied by:
- tests first
- an ExecPlan for complex work in `docs/exec-plans/`
- updated quality and reliability docs
