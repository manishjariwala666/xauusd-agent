# Phase P6.0 apply notes

This bundle is additive and schema/skeleton-only.

Files to add to the repository:

- `migrations/007_master_ai_orchestrator.sql`
- `services/master_orchestrator.py`
- `services/execution_planner.py`
- `services/execution_graph.py`
- `services/orchestration_memory.py`
- `services/shared_task_context.py`
- `services/agent_message_bus.py`
- `services/orchestration_notifications.py`
- `services/worker_agent_adapter.py`
- `tests/test_master_ai_schema_compatibility.py`

If `services/migration_service.py` maintains a hard-coded migration filename
list, add `"007_master_ai_orchestrator.sql"` after `"006_production_agents.sql"`.

Suggested small commits after applying:

1. `git add migrations/007_master_ai_orchestrator.sql && git commit -m "Add Master AI orchestrator schema"`
2. `git add services/master_orchestrator.py services/execution_planner.py services/execution_graph.py services/orchestration_memory.py services/shared_task_context.py services/agent_message_bus.py services/orchestration_notifications.py services/worker_agent_adapter.py && git commit -m "Add Master AI service skeletons"`
3. `git add tests/test_master_ai_schema_compatibility.py && git commit -m "Add Master AI schema compatibility tests"`
4. If needed: `git add services/migration_service.py && git commit -m "Register Master AI migration"`

Do not add `.env`, `service_account.json`, private keys, or credential files.
