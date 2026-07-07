# Phase P6.1 apply notes

This bundle implements the Master AI orchestration engine on top of the Phase P6.0 schema/skeletons.

Scope:

- Existing worker agents are not replaced.
- Existing direct/manual/scheduled agent execution remains backward compatible.
- Master AI delegates worker execution through `services.worker_agent_adapter.WorkerAgentAdapter`.
- Orchestration state is stored only in the `master_ai_*` tables from Phase P6.0.
- No Railway, Supabase, Telegram, WhatsApp, environment, private-key, or credential files are changed.

Files modified/added:

- `services/master_orchestrator.py`
- `services/execution_planner.py`
- `services/execution_graph.py`
- `services/orchestration_memory.py`
- `services/shared_task_context.py`
- `services/agent_message_bus.py`
- `services/orchestration_notifications.py`
- `services/worker_agent_adapter.py`
- `services/orchestration_redaction.py`
- `tests/test_master_ai_execution_engine.py`
- Optional dashboard patch snippet: `admin_dashboard_p6_1.patch`

Apply order:

```bash
cd /Users/manissh/Desktop/xauusd-agent

# Ensure Phase P6.0 is already applied and migration 007 is registered.
git status --short

git apply /path/to/phase_p6_1_additive.patch

# Optional if the dashboard hunk does not apply cleanly:
# git apply /path/to/admin_dashboard_p6_1.patch
# or manually add the Master AI panel from the patch.

pytest -q
```

Suggested small commits:

```bash
git add services/orchestration_redaction.py services/execution_planner.py
git commit -m "Implement Master AI planning and redaction"

git add services/execution_graph.py services/orchestration_memory.py services/shared_task_context.py services/agent_message_bus.py
git commit -m "Add Master AI persistence services"

git add services/worker_agent_adapter.py services/orchestration_notifications.py services/master_orchestrator.py
git commit -m "Implement Master AI execution engine"

git add tests/test_master_ai_execution_engine.py
git commit -m "Add Master AI execution engine tests"

# Only after reviewing the dashboard hunk locally:
git add admin/dashboard.py
git commit -m "Integrate Master AI progress into admin dashboard"

git push origin main
```

Do not add:

- environment files
- service-account JSON files
- private key files
- downloaded credentials
