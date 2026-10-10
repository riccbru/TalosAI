"""Background execution + live event fan-out for hybrid missions.

The orchestrator is fully synchronous (blocking Docker exec, time.sleep, sync
Gemini client), so each mission runs in its own daemon thread. Persistence and
live streaming both cross the thread boundary back onto the main asyncio loop:

  * DB writes  -> asyncio.run_coroutine_threadsafe(...).result()  (reuses asyncpg)
  * WS events  -> loop.call_soon_threadsafe(_broadcast, ...)      (per-mission queues)

This keeps every reasoning step, action and finding durable in the DB *and*
visible live, so a crash still leaves a resumable, retrievable mission.
"""
import asyncio
import threading
import traceback
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from app.agents.hybrid_orchestrator_v2 import HybridOrchestratorV2
from app.agents.mission_exceptions import MissionCancelled
from app.crud import crud_missions
from app.db.session import AsyncSessionLocal

# mission_uuid (str) -> set of live subscriber queues
_subscribers: Dict[str, Set["asyncio.Queue"]] = {}
_subscribers_lock = threading.Lock()

# mission_uuid (str) -> stop flag for the running worker thread (this process only)
_cancel_events: Dict[str, threading.Event] = {}
_cancel_lock = threading.Lock()


def request_cancel(mission_uuid: str) -> bool:
    """Signal a running worker to stop at its next checkpoint.

    Returns True if a live worker in THIS process was signalled, False if none
    is tracked here (e.g. the mission's thread died with the process, so the
    caller should mark it interrupted in the DB directly).
    """
    with _cancel_lock:
        event = _cancel_events.get(str(mission_uuid))
    if event is None:
        return False
    event.set()
    return True


def subscribe(mission_uuid: str) -> "asyncio.Queue":
    """Register a live listener. Call from the event loop (e.g. a WS handler)."""
    queue: asyncio.Queue = asyncio.Queue()
    with _subscribers_lock:
        _subscribers.setdefault(mission_uuid, set()).add(queue)
    return queue


def unsubscribe(mission_uuid: str, queue: "asyncio.Queue") -> None:
    with _subscribers_lock:
        subs = _subscribers.get(mission_uuid)
        if subs:
            subs.discard(queue)
            if not subs:
                _subscribers.pop(mission_uuid, None)


def _broadcast(mission_uuid: str, event: dict) -> None:
    """Runs on the loop thread (via call_soon_threadsafe)."""
    with _subscribers_lock:
        subs = list(_subscribers.get(mission_uuid, ()))
    for queue in subs:
        queue.put_nowait(event)


class DBReporter:
    """Sink the orchestrator writes to. Persists durable state and streams events."""

    def __init__(self, mission_uuid: str, loop: asyncio.AbstractEventLoop):
        self.mission_uuid = mission_uuid
        self.loop = loop

    # --- cross-thread plumbing ---

    def _publish(self, event: dict) -> None:
        event.setdefault("mission_uuid", self.mission_uuid)
        event.setdefault("ts", datetime.now(timezone.utc).isoformat())
        try:
            self.loop.call_soon_threadsafe(_broadcast, self.mission_uuid, event)
        except RuntimeError:
            pass  # loop gone; nothing to stream to

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout=30)

    # --- orchestrator-facing API ---

    def log(self, step: str, message: str, status: str = "running") -> None:
        print(f"\n[TALOSAI_LOG] [{status.upper()}] {step} -> {message}", flush=True)
        self._publish(
            {"type": "log", "step": step, "status": status, "message": message}
        )

    def services_discovered(self, services: List[dict]) -> None:
        try:
            self._run(self._persist_services(services))
        except Exception as e:  # noqa: BLE001 - never kill the mission over telemetry
            print(f"[mission_runner] persist services failed: {e}", flush=True)
        self._publish(
            {
                "type": "services",
                "services": [
                    {
                        "port": s["port"],
                        "service_name": s.get("service_name"),
                        "version": s.get("version"),
                    }
                    for s in services
                ],
            }
        )

    def finding(self, data: dict) -> None:
        saved_uuid = None
        try:
            saved_uuid = self._run(self._persist_finding(data))
        except Exception as e:  # noqa: BLE001
            print(f"[mission_runner] persist finding failed: {e}", flush=True)
        self._publish({"type": "finding", "finding": {**data, "uuid": saved_uuid}})

    def port_status(
        self, port: int, status: str, attempts: int, history: List[dict]
    ) -> None:
        try:
            self._run(self._persist_port(port, status, attempts, history))
        except Exception as e:  # noqa: BLE001
            print(f"[mission_runner] persist port failed: {e}", flush=True)
        self._publish(
            {
                "type": "port_status",
                "port": port,
                "status": status,
                "attempts": attempts,
            }
        )

    def mission_status(self, status: str, error: Optional[str] = None) -> None:
        try:
            self._run(self._persist_mission_status(status, error))
        except Exception as e:  # noqa: BLE001
            print(f"[mission_runner] persist mission status failed: {e}", flush=True)
        self._publish({"type": "mission_status", "status": status, "error": error})

    # --- persistence coroutines (each uses its own session on the loop) ---

    async def _persist_services(self, services: List[dict]) -> None:
        async with AsyncSessionLocal() as db:
            await crud_missions.replace_ports(db, self.mission_uuid, services)
            await crud_missions.set_discovered(db, self.mission_uuid, True)
            await db.commit()

    async def _persist_finding(self, data: dict) -> str:
        async with AsyncSessionLocal() as db:
            finding = await crud_missions.add_finding(db, self.mission_uuid, data)
            await db.commit()
            return str(finding.uuid)

    async def _persist_port(
        self, port: int, status: str, attempts: int, history: List[dict]
    ) -> None:
        async with AsyncSessionLocal() as db:
            await crud_missions.update_port(
                db, self.mission_uuid, port, status, attempts, history
            )
            await db.commit()

    async def _persist_mission_status(
        self, status: str, error: Optional[str]
    ) -> None:
        async with AsyncSessionLocal() as db:
            await crud_missions.update_mission_status(
                db, self.mission_uuid, status, error=error
            )
            await db.commit()


def _load_services(mission_uuid: str, loop: asyncio.AbstractEventLoop) -> List[dict]:
    async def _load():
        async with AsyncSessionLocal() as db:
            ports = await crud_missions.get_ports(db, mission_uuid)
            return [
                {
                    "port": p.port,
                    "service_name": p.service_name,
                    "version": p.version,
                    "status": p.status,
                    "attempts": p.attempts,
                    "history": p.history or [],
                }
                for p in ports
            ]

    return asyncio.run_coroutine_threadsafe(_load(), loop).result(timeout=30)


def _worker(
    mission_uuid: str,
    scan_target: str,
    prompt: Optional[str],
    loop: asyncio.AbstractEventLoop,
    resume: bool,
    cancel_event: threading.Event,
) -> None:
    reporter = DBReporter(mission_uuid, loop)
    try:
        if cancel_event.is_set():  # cancelled before we even started
            reporter.mission_status("interrupted")
            return
        reporter.mission_status("running")
        initial_services = _load_services(mission_uuid, loop) if resume else None
        orchestrator = HybridOrchestratorV2(
            target=scan_target,
            user_prompt=prompt,
            reporter=reporter,
            initial_services=initial_services,
            should_cancel=cancel_event.is_set,
        )
        orchestrator.run()
        reporter.mission_status("completed")
    except MissionCancelled:
        reporter.log("Manager", "Mission stopped by user request.", "interrupted")
        reporter.mission_status("interrupted")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        reporter.mission_status("failed", error=str(e))
    finally:
        with _cancel_lock:
            _cancel_events.pop(mission_uuid, None)


def launch(
    *,
    mission_uuid,
    scan_target: str,
    prompt: Optional[str],
    loop: asyncio.AbstractEventLoop,
    resume: bool = False,
) -> None:
    key = str(mission_uuid)
    cancel_event = threading.Event()
    with _cancel_lock:
        _cancel_events[key] = cancel_event
    thread = threading.Thread(
        target=_worker,
        args=(key, scan_target, prompt, loop, resume, cancel_event),
        name=f"mission-{mission_uuid}",
        daemon=True,
    )
    thread.start()
