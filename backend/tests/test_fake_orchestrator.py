"""Unit tests for the fake mission engine and its orchestration loop.

The real HybridOrchestratorV2 can't be imported in this env (Gemini/CrewAI),
but the fake engine is dependency-free and emits the identical reporter call
sequence, so these tests cover the discovery -> findings -> cancel -> resume
mechanism directly. STEP_DELAY is zeroed so they run instantly.
"""
import pytest

import app.agents.fake_orchestrator as fake_mod
from app.agents.fake_orchestrator import FakeOrchestratorV2, FAKE_SERVICES
from app.agents.mission_exceptions import MissionCancelled


@pytest.fixture(autouse=True)
def _no_delay(monkeypatch):
    monkeypatch.setattr(fake_mod, "STEP_DELAY_SECONDS", 0)


class RecordingReporter:
    def __init__(self):
        self.events = []

    def log(self, step, message, status="running"):
        self.events.append(("log", step, status))

    def services_discovered(self, services):
        self.events.append(("services", [s["port"] for s in services]))

    def finding(self, data):
        self.events.append(("finding", data["port"], data["confirmed"]))

    def port_status(self, port, status, attempts, history):
        self.events.append(("port_status", port, status, attempts))

    def mission_status(self, status, error=None):
        self.events.append(("mission_status", status))

    def of(self, kind):
        return [e for e in self.events if e[0] == kind]


def test_full_run_discovers_and_produces_findings():
    reporter = RecordingReporter()
    result = FakeOrchestratorV2(target="t", reporter=reporter).run()

    assert result["status"] == "completed"
    # one discovery event listing every fake port
    assert reporter.of("services") == [("services", [s["port"] for s in FAKE_SERVICES])]
    # two findings per service
    assert len(reporter.of("finding")) == 2 * len(FAKE_SERVICES)
    # each port ends 'completed'
    completed = [e for e in reporter.of("port_status") if e[2] == "completed"]
    assert {e[1] for e in completed} == {s["port"] for s in FAKE_SERVICES}
    # the ftp port is flagged confirmed
    assert ("finding", 21, True) in reporter.of("finding")


def test_cancel_raises_and_stops_early():
    reporter = RecordingReporter()
    calls = {"n": 0}

    def should_cancel():
        calls["n"] += 1
        return calls["n"] >= 4  # trip after a few checkpoints

    with pytest.raises(MissionCancelled):
        FakeOrchestratorV2(
            target="t", reporter=reporter, should_cancel=should_cancel
        ).run()

    # it did real work before stopping, but not the full run
    assert 0 < len(reporter.of("finding")) < 2 * len(FAKE_SERVICES)
    assert reporter.of("mission_status") == []  # terminal status is the worker's job


def test_resume_skips_completed_ports():
    reporter = RecordingReporter()
    initial = [
        {"port": 21, "service_name": "ftp", "version": "x",
         "status": "completed", "attempts": 2, "history": []},
        {"port": 22, "service_name": "ssh", "version": "y",
         "status": "pending", "attempts": 0, "history": []},
    ]
    result = FakeOrchestratorV2(
        target="t", reporter=reporter, initial_services=initial
    ).run()

    assert result["status"] == "completed"
    # no re-discovery on resume
    assert reporter.of("services") == []
    # only the pending port (22) is investigated
    investigated = {e[1] for e in reporter.of("finding")}
    assert investigated == {22}
    completed = {e[1] for e in reporter.of("port_status") if e[2] == "completed"}
    assert completed == {22}
