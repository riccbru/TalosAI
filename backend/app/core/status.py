import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone

import docker
import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.ollama import ollama_client


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_backend_status() -> dict:
    warnings = []
    t0 = time.perf_counter()
    latency_ms = round((time.perf_counter() - t0) * 1000, 3)

    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    if cpu_percent > 85:
        warnings.append("high_cpu")
    if mem.percent > 90:
        warnings.append("high_memory")

    total_disk, used_disk, free_disk = shutil.disk_usage("/")
    if (free_disk / total_disk) < 0.10:
        warnings.append("low_disk")

    gpus = None
    try:
        import pynvml

        gpus = []
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        gpus = []
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)

            gpus.append(
                {
                    "id": i,
                    "name": name,
                    "memory_used_gb": round(info.used / 1024**3, 2),
                    "memory_total_gb": round(info.total / 1024**3, 2),
                    "load_percent": util.gpu,
                }
            )
    except (FileNotFoundError, subprocess.SubprocessError, Exception):
        gpus = "unavailable"

    return {
        "status": "degraded" if warnings else "up",
        "latency_ms": latency_ms,
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
        },
        "cpu": {
            "usage_percent": cpu_percent,
            "load_avg": list(psutil.getloadavg()),
        },
        "memory": {
            "used_percent": mem.percent,
            "available_gb": round(mem.available / 2**30, 2),
        },
        "disk": {
            "free_gb": round(free_disk / 2**30, 2),
            "used_percent": round(used_disk / total_disk * 100, 1),
        },
        "gpu": gpus,
        "warnings": warnings,
    }


async def get_db_status(db: AsyncSession, engine: AsyncEngine) -> dict:
    warnings = []
    t0 = time.perf_counter()

    db_version = "Unknown"
    pool_stats = {}
    connection_state = "disconnected"

    try:
        result = await db.execute(text("SELECT version()"))
        db_version = result.scalar()
        latency_ms = round((time.perf_counter() - t0) * 1000, 3)
        connection_state = "connected"

        raw_pool = engine.sync_engine.pool
        for attr in ("size", "checkedin", "checkedout", "overflow"):
            if hasattr(raw_pool, attr):
                pool_stats[attr] = getattr(raw_pool, attr)()

        checked_out = pool_stats.get("checkedout", 0)
        pool_size = pool_stats.get("size", 1)
        if pool_size > 0 and (checked_out / pool_size) > 0.85:
            warnings.append("pool_near_capacity")
        if latency_ms > 200:
            warnings.append("high_query_latency")

    except Exception as e:
        connection_state = "disconnected"
        warnings.append(f"connection_error: {str(e)}")

    return {
        "status": "up",
        "timestamp": _utc_now(),
        "connection": {
            "state": connection_state,
            "latency_ms": latency_ms,
        },
        "version": db_version,
        "pool": pool_stats,
        "warnings": warnings,
    }


async def get_ollama_status() -> dict:

    try:
        t0 = time.perf_counter()

        models_library = await ollama_client.list()
        active_models = await ollama_client.ps()

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "status": "up",
            "timestamp": _utc_now(),
            "latency_ms": latency_ms,
            "summary": {
                "total_installed": len(models_library.models),
                "currently_active": len(active_models.models),
            },
            "active_models": active_models.get("models", []),
            "library": models_library.get("models", []),
        }

    except Exception as e:
        return {"status": "down", "error": type(e).__name__, "message": str(e)}


async def get_kali_status():
    t0 = time.perf_counter()
    try:
        client = docker.from_env()
        container = client.containers.get("talos_kali")
        attrs = container.attrs
        state = attrs.get("State", {})

        networks = attrs.get("NetworkSettings", {}).get("Networks", {})
        target_net = networks.get("talos_network")
        # high latency: 1800ms???
        # stats = container.stats(stream=False)
        # cpu_usage = stats['cpu_stats']['cpu_usage']['total_usage']
        mem_limit = attrs["HostConfig"]["Memory"]

        latency_ms = round((time.perf_counter() - t0) * 1000, 3)

        return {
            "status": "up" if state.get("Status") == "running" else "down",
            "timestamp": _utc_now(),
            "latency_ms": latency_ms,
            "network": {
                "gateway": target_net.get("Gateway"),
                "ip_address": target_net.get("IPAddress"),
                "mac_address": target_net.get("MacAddress"),
                "internal_name": next(iter(networks.keys())) if networks else "none",
            },
            "resources": {
                # "cpu_usage_percent": cpu_usage,
                "memory_usage_mb": (
                    round(mem_limit / (1024**2), 2) if mem_limit > 0 else "unlimited"
                )
            },
        }
    except Exception as e:
        return {"status": "down", "error": type(e).__name__, "message": str(e)}


async def get_metapsloitable_status():
    t0 = time.perf_counter()
    try:
        client = docker.from_env()
        container = client.containers.get("talos_metasploitable")
        attrs = container.attrs
        state = attrs.get("State", {})
        networks = attrs.get("NetworkSettings", {}).get("Networks", {})
        target_net = networks.get("talos_network", {})
        mem_limit = attrs["HostConfig"]["Memory"]

        latency_ms = round((time.perf_counter() - t0) * 1000, 3)

        return {
            "status": "up" if state.get("Status") == "running" else "down",
            "timestamp": _utc_now(),
            "latency_ms": latency_ms,
            "network": {
                "gateway": target_net.get("Gateway"),
                "ip_address": target_net.get("IPAddress"),
                "mac_address": target_net.get("MacAddress"),
                "internal_name": next(iter(networks.keys())) if networks else "none",
            },
            "resources": {
                "memory_usage_mb": (
                    round(mem_limit / (1024**2), 2) if mem_limit > 0 else "unlimited"
                )
            },
        }
    except Exception as e:
        return {"status": "down", "error": type(e).__name__, "message": str(e)}


def get_service_error(e: Exception) -> dict:
    return {
        "status": "down",
        "timestamp": _utc_now(),
        "error": type(e).__name__,
        "message": e.args[-1] if e.args else str(e),
    }
