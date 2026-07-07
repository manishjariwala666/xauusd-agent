"""Phase P6.1 Master AI execution-engine unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from services.execution_graph import ExecutionGraphNode
from services.execution_planner import AgentDescriptor, ExecutionPlanner
from services.master_orchestrator import MasterOrchestrator, OrchestrationProgress
from services.orchestration_redaction import REDACTED, redact_value
from services.worker_agent_adapter import WorkerAgentResult


class FakeGraph:
    def __init__(self) -> None:
        self.steps: list[ExecutionGraphNode] = []
        self.status_by_id: dict[int, str] = {}
        self.marked: list[tuple[int, str]] = []

    def create_graph(self, *, orchestration_run_id: int, plan):
        self.steps = [
            ExecutionGraphNode(
                step_key=step.step_key,
                agent_key=step.agent_key,
                status="READY" if not step.depends_on else "PENDING",
                metadata={
                    "id": index,
                    "attempt_count": 0,
                    "max_attempts": int(step.retry_policy.get("max_attempts", 1)),
                    "can_run_parallel": step.can_run_parallel,
                },
            )
            for index, step in enumerate(plan.steps, start=1)
        ]
        self.status_by_id = {int(step.metadata["id"]): step.status for step in self.steps}
        return None

    def get_runnable_steps(self, *, orchestration_run_id: int):
        runnable = []
        for step in self.steps:
            step_id = int(step.metadata["id"])
            if self.status_by_id.get(step_id) in {"READY", "PENDING"}:
                runnable.append(step)
        return runnable

    def mark_step_status(self, *, step_id: int, status: str, result=None, error=None):
        self.status_by_id[step_id] = status
        self.marked.append((step_id, status))
        for index, step in enumerate(self.steps):
            if int(step.metadata["id"]) == step_id:
                metadata = dict(step.metadata)
                if status == "RUNNING":
                    metadata["attempt_count"] = int(metadata.get("attempt_count") or 0) + 1
                self.steps[index] = ExecutionGraphNode(
                    step_key=step.step_key,
                    agent_key=step.agent_key,
                    status=status,
                    metadata=metadata,
                )
                break


class FakeContext:
    def __init__(self) -> None:
        self.outputs: dict[str, dict] = {}

    def initialize_context(self, *, orchestration_run_id: int, input_payload: dict) -> int:
        return 1

    def get_context_for_agent(self, *, orchestration_run_id: int, agent_key: str, step_key: str) -> dict:
        return {"agent_key": agent_key, "step_key": step_key, "token": "must-redact"}

    def merge_step_output(self, *, orchestration_run_id: int, step_key: str, output: dict) -> int:
        self.outputs[step_key] = output
        return len(self.outputs) + 1


class FakeMemory:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []

    def append_entry(self, *, orchestration_run_id: int, entry_type: str, summary: str, data, created_by: str) -> None:
        self.entries.append((entry_type, summary))


class FakeBus:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    def send_message(self, *, orchestration_run_id: int, from_agent_key: str, to_agent_key: str, message_type: str, payload: dict) -> int:
        self.messages.append((from_agent_key, to_agent_key, message_type))
        return len(self.messages)


class FakeNotifications:
    def __init__(self) -> None:
        self.events: list[str] = []

    def notify_started(self, run_id: int) -> None:
        self.events.append(f"started:{run_id}")

    def notify_approval_required(self, approval_id: int) -> None:
        self.events.append(f"approval:{approval_id}")

    def notify_failed(self, run_id: int, safe_error: str) -> None:
        self.events.append(f"failed:{run_id}")

    def notify_completed(self, run_id: int, summary: str) -> None:
        self.events.append(f"completed:{run_id}")


class FakeWorker:
    def __init__(self, results: list[WorkerAgentResult]) -> None:
        self.results = results
        self.calls: list[str] = []

    def execute_step(self, *, agent_key: str, trigger_type: str, triggered_by, payload: dict, orchestration_run_id=None, orchestration_step_id=None):
        self.calls.append(agent_key)
        return self.results.pop(0)


class _TestableOrchestrator(MasterOrchestrator):
    def __init__(self, progress: OrchestrationProgress, **kwargs) -> None:
        super().__init__(**kwargs)
        self.progress = progress
        self.status_updates: list[str] = []

    def _update_run_status(self, orchestration_run_id: int, status: str, **kwargs) -> None:
        self.status_updates.append(status)
        self.progress = OrchestrationProgress(
            run_id=self.progress.run_id,
            task_id=self.progress.task_id,
            status=status,
            completed_steps=sum(1 for step_id, step_status in self.graph.status_by_id.items() if step_status == "COMPLETED"),
            total_steps=len(self.graph.status_by_id),
            failed_steps=sum(1 for step_id, step_status in self.graph.status_by_id.items() if step_status == "FAILED"),
        )


def test_redaction_removes_nested_secrets() -> None:
    payload = {"api_key": "abc", "nested": {"token": "secret", "safe": "ok"}}
    redacted = redact_value(payload)
    assert redacted["api_key"] == REDACTED
    assert redacted["nested"]["token"] == REDACTED
    assert redacted["nested"]["safe"] == "ok"


def test_planner_uses_explicit_agent_order_and_parallel_flag() -> None:
    planner = ExecutionPlanner()
    task = type(
        "Task",
        (),
        {
            "task_type": "CUSTOM",
            "title": "Run customer workflow",
            "input_payload": {"agent_keys": ["telegram_reply", "blog_agent"], "parallel": True, "max_attempts": 3},
        },
    )()
    plan = planner.build_plan(
        task=task,
        available_agents=[
            AgentDescriptor("telegram_reply", "Telegram Reply"),
            AgentDescriptor("blog_agent", "Blog Agent"),
        ],
        context={},
    )
    assert [step.agent_key for step in plan.steps] == ["telegram_reply", "blog_agent"]
    assert all(step.can_run_parallel for step in plan.steps)
    assert all(step.retry_policy["max_attempts"] == 3 for step in plan.steps)
    assert planner.validate_plan(plan=plan).is_valid


def test_orchestrator_executes_workers_and_records_messages() -> None:
    graph = FakeGraph()
    planner = ExecutionPlanner()
    task = type(
        "Task",
        (),
        {"task_type": "CUSTOM", "title": "Run workflow", "input_payload": {"agent_keys": ["a1"], "parallel": False}},
    )()
    plan = planner.build_plan(
        task=task,
        available_agents=[AgentDescriptor("a1", "Agent 1")],
        context={},
    )
    graph.create_graph(orchestration_run_id=10, plan=plan)
    worker = FakeWorker([WorkerAgentResult(True, "ok", "done", {"safe": "yes"})])
    memory = FakeMemory()
    bus = FakeBus()
    notifications = FakeNotifications()
    orchestrator = _TestableOrchestrator(
        progress=OrchestrationProgress(10, 1, "PLAN_READY", 0, 1),
        planner=planner,
        graph=graph,
        context=FakeContext(),
        memory=memory,
        message_bus=bus,
        notifications=notifications,
        worker_adapter=worker,
    )
    orchestrator._execute_until_blocked_or_complete(10)
    assert worker.calls == ["a1"]
    assert graph.status_by_id[1] == "COMPLETED"
    assert ("a1", "MASTER_AI", "STEP_OUTPUT") in bus.messages
    assert any(entry_type == "STEP_COMPLETED" for entry_type, _ in memory.entries)
