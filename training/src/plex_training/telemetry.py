"""Runtime and peak-memory reporting without optional monitoring packages."""

from __future__ import annotations

import ctypes
import os
import platform
import sys
from typing import Any

import torch


def select_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but this PyTorch runtime cannot access it")
    if requested not in {"cpu", "cuda"}:
        raise ValueError("device must be auto, cpu, or cuda")
    return torch.device(requested)


def process_peak_working_set_bytes() -> int | None:
    """Return this process's peak working set on Windows, when available."""
    if sys.platform != "win32":
        return None

    class MemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    try:
        psapi = ctypes.WinDLL("Psapi.dll")
        kernel32 = ctypes.WinDLL("Kernel32.dll")
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(MemoryCounters),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        counters = MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = kernel32.GetCurrentProcess()
        success = psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
        return int(counters.PeakWorkingSetSize) if success else None
    except (AttributeError, OSError):
        return None


def environment_report(device: torch.device | None = None) -> dict[str, Any]:
    cuda_available = torch.cuda.is_available()
    selected = device or torch.device("cuda" if cuda_available else "cpu")
    gpu: dict[str, Any] | None = None
    if cuda_available:
        index = (
            selected.index
            if selected.type == "cuda" and selected.index is not None
            else torch.cuda.current_device()
        )
        properties = torch.cuda.get_device_properties(index)
        free_bytes, total_bytes = torch.cuda.mem_get_info(index)
        gpu = {
            "name": properties.name,
            "totalBytes": int(total_bytes),
            "freeBytesAtReport": int(free_bytes),
            "computeCapability": f"{properties.major}.{properties.minor}",
        }
    return {
        "pythonVersion": platform.python_version(),
        "platform": sys.platform,
        "plexTrainingVersion": "0.1.0",
        "torchVersion": str(torch.__version__),
        "torchCudaRuntime": torch.version.cuda,
        "cudaAvailable": cuda_available,
        "selectedDevice": str(selected),
        "gpu": gpu,
        "processPeakWorkingSetBytes": process_peak_working_set_bytes(),
        "threadCount": os.cpu_count(),
    }


def reset_peak_gpu_memory(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        torch.cuda.reset_peak_memory_stats(device)


def peak_gpu_memory(device: torch.device) -> dict[str, int] | None:
    if device.type != "cuda":
        return None
    torch.cuda.synchronize(device)
    return {
        "allocatedBytes": int(torch.cuda.max_memory_allocated(device)),
        "reservedBytes": int(torch.cuda.max_memory_reserved(device)),
    }
