import asyncio
import shutil
import subprocess
import time
from datetime import datetime, timezone

import httpx
import psutil
import pynvml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.config import settings


def _utc_now():
    return datetime.now(timezone.utc).isoformat()

def get_system_stats() -> dict:
    warnings = []

    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    if cpu_percent > 85: warnings.append("high_cpu")
    if mem.percent > 90: warnings.append("high_memory")

    total_disk, used_disk, free_disk = shutil.disk_usage("/")
    if (free_disk / total_disk) < 0.10: warnings.append("low_disk")

    gpus = None
    try:
        # out = subprocess.check_output(
        #     [
        #         "nvidia-smi",
        #         "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
        #         "--format=csv,noheader,nounits",
        #     ],
        #     timeout=2,
        #     stderr=subprocess.DEVNULL,
        # ).decode()

        # gpus = []
        # for line in out.strip().splitlines():
        #     name, util, mem_used, mem_total, temp, power = [x.strip() for x in line.split(",")]  # noqa: E501
        #     vram_used, vram_total = int(mem_used), int(mem_total)

        #     gpu_warnings = []
        #     if int(util) > 95: gpu_warnings.append("high_gpu_utilization")
        #     if vram_total and (vram_used / vram_total) > 0.92: gpu_warnings.append("vram_near_full")  # noqa: E501
        #     if int(temp) > 85: gpu_warnings.append("high_temperature")

        #     warnings.extend(gpu_warnings)
        #     gpus.append({
        #         "name": name,
        #         "utilization_percent": int(util),
        #         "vram_used_mb": vram_used,
        #         "vram_total_mb": vram_total,
        #         "vram_used_percent": round(vram_used / vram_total * 100, 1) if vram_total else None,
        #         "temperature_c": int(temp),
        #         "power_draw_w": round(float(power), 1),
        #         "warnings": gpu_warnings,
        #     })
        gpus = []
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        gpus = []
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)

            gpus.append({
                "id": i,
                "name": name,
                "memory_used_gb": round(info.used / 1024**3, 2),
                "memory_total_gb": round(info.total / 1024**3, 2),
                "load_percent": util.gpu
            })
    except (FileNotFoundError, subprocess.SubprocessError):
        gpus = "unavailable"

    return {
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
        "warnings": warnings
    }

async def get_db_stats(db: AsyncSession, engine: AsyncEngine) -> dict:
    t0 = time.perf_counter()
    warnings = []

    try:
        result = await db.execute(text("SELECT version()"))
        db_version = result.scalar()
        latency_ms = round((time.perf_counter() - t0) * 1000, 3)

        raw_pool = engine.sync_engine.pool
        pool_stats = {}
        for attr in ("size", "checkedin", "checkedout", "overflow"):
            if hasattr(raw_pool, attr):
                pool_stats[attr] = getattr(raw_pool, attr)()

        checked_out = pool_stats.get("checkedout", 0)
        pool_size = pool_stats.get("size", 1)

        if pool_size > 0 and (checked_out / pool_size) > 0.85:
            warnings.append("pool_near_capacity")
        if latency_ms > 200:
            warnings.append("high_query_latency")

        return {
            "status": "degraded" if warnings else "connected",
            "latency_ms": latency_ms,
            "version": db_version,
            "pool": pool_stats,
            "warnings": warnings
        }

    except Exception as e:
        raise e

async def get_ollama_stats() -> dict:
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            t0 = time.perf_counter()

            responses = await asyncio.gather(
                client.get(f"{base_url}/api/tags"),
                client.get(f"{base_url}/api/ps"),
                return_exceptions=True
            )

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            for r in responses:
                if isinstance(r, Exception):
                    raise r
                r.raise_for_status()

            library_data = responses[0].json()
            active_data = responses[1].json()

            library = [
                {
                    "name": m.get("name"),
                    "size_gb": round(m.get("size", 0) / 1024**3, 2),
                    "modified": m.get("modified_at")
                }
                for m in library_data.get("models", [])
            ]

            active = [
                {
                    "name": m.get("name"),
                    "vram_gb": round(m.get("size_vram", 0) / 1024**3, 2),
                    "expires_at": m.get("expires_at")
                }
                for m in active_data.get("models", [])
            ]

            return {
                "status": "up",
                "latency_ms": latency_ms,
                "summary": {
                    "total_installed": len(library),
                    "currently_active": len(active)
                },
                "active_models": active,
                "library": library
            }

    except Exception as e:
        return {
            "status": "down",
            "error": type(e).__name__,
            "message": str(e)
        }

def get_service_error(e: Exception) -> dict:
    return {
        "status": "down",
        "timestamp": _utc_now(),
        "error": type(e).__name__,
        "message": e.args[-1] if e.args else str(e),
        }
