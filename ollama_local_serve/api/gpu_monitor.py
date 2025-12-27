"""
GPU and System Monitoring utilities for Ollama Local Serve.

Provides GPU metrics collection using nvidia-smi or pynvml.
Provides CPU and RAM metrics using psutil.
Gracefully degrades when no GPU is available.
"""

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """GPU information from nvidia-smi."""

    index: int
    name: str
    driver_version: str
    cuda_version: str
    memory_total_mb: int
    memory_used_mb: int
    memory_free_mb: int
    utilization_gpu: int  # percentage
    utilization_memory: int  # percentage
    temperature_gpu: int  # Celsius
    power_draw_w: float
    power_limit_w: float

    @property
    def memory_utilization_percent(self) -> float:
        """Calculate memory utilization percentage."""
        if self.memory_total_mb == 0:
            return 0.0
        return (self.memory_used_mb / self.memory_total_mb) * 100

    @property
    def vram_used_gb(self) -> float:
        """Get VRAM used in GB."""
        return self.memory_used_mb / 1024

    @property
    def vram_total_gb(self) -> float:
        """Get total VRAM in GB."""
        return self.memory_total_mb / 1024

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "index": self.index,
            "name": self.name,
            "driver_version": self.driver_version,
            "cuda_version": self.cuda_version,
            "memory_total_mb": self.memory_total_mb,
            "memory_used_mb": self.memory_used_mb,
            "memory_free_mb": self.memory_free_mb,
            "memory_utilization_percent": round(self.memory_utilization_percent, 1),
            "utilization_gpu_percent": self.utilization_gpu,
            "utilization_memory_percent": self.utilization_memory,
            "temperature_celsius": self.temperature_gpu,
            "power_draw_watts": round(self.power_draw_w, 1),
            "power_limit_watts": round(self.power_limit_w, 1),
            "vram_used_gb": round(self.vram_used_gb, 2),
            "vram_total_gb": round(self.vram_total_gb, 2),
        }


@dataclass
class GPUMetrics:
    """Aggregated GPU metrics for the system."""

    available: bool = False
    gpu_count: int = 0
    gpus: list[GPUInfo] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None

    # Aggregate metrics (for single GPU systems)
    @property
    def total_vram_gb(self) -> float:
        """Total VRAM across all GPUs in GB."""
        return sum(gpu.vram_total_gb for gpu in self.gpus)

    @property
    def used_vram_gb(self) -> float:
        """Used VRAM across all GPUs in GB."""
        return sum(gpu.vram_used_gb for gpu in self.gpus)

    @property
    def avg_gpu_utilization(self) -> float:
        """Average GPU utilization across all GPUs."""
        if not self.gpus:
            return 0.0
        return sum(gpu.utilization_gpu for gpu in self.gpus) / len(self.gpus)

    @property
    def avg_temperature(self) -> float:
        """Average temperature across all GPUs."""
        if not self.gpus:
            return 0.0
        return sum(gpu.temperature_gpu for gpu in self.gpus) / len(self.gpus)

    @property
    def avg_memory_utilization(self) -> float:
        """Average memory utilization across all GPUs."""
        if not self.gpus:
            return 0.0
        return sum(gpu.memory_utilization_percent for gpu in self.gpus) / len(self.gpus)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "available": self.available,
            "gpu_count": self.gpu_count,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
            # Aggregate metrics
            "total_vram_gb": round(self.total_vram_gb, 2),
            "used_vram_gb": round(self.used_vram_gb, 2),
            "avg_gpu_utilization_percent": round(self.avg_gpu_utilization, 1),
            "avg_memory_utilization_percent": round(self.avg_memory_utilization, 1),
            "avg_temperature_celsius": round(self.avg_temperature, 1),
            # Per-GPU details
            "gpus": [gpu.to_dict() for gpu in self.gpus],
        }


class GPUMonitor:
    """
    Monitor GPU metrics using nvidia-smi.

    Supports caching to avoid excessive subprocess calls.
    Gracefully handles systems without NVIDIA GPUs.
    """

    def __init__(self, cache_ttl_seconds: float = 2.0):
        """
        Initialize GPU monitor.

        Args:
            cache_ttl_seconds: How long to cache GPU metrics (default 2s)
        """
        self._cache_ttl = cache_ttl_seconds
        self._cached_metrics: GPUMetrics | None = None
        self._cache_timestamp: float = 0
        self._nvidia_smi_available: bool | None = None
        self._pynvml_available: bool | None = None

    def _check_nvidia_smi(self) -> bool:
        """Check if nvidia-smi is available."""
        if self._nvidia_smi_available is not None:
            return self._nvidia_smi_available

        try:
            result = subprocess.run(
                ["nvidia-smi", "--version"],
                capture_output=True,
                timeout=5,
            )
            self._nvidia_smi_available = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            self._nvidia_smi_available = False

        return self._nvidia_smi_available

    async def get_metrics(self, force_refresh: bool = False) -> GPUMetrics:
        """
        Get current GPU metrics.

        Args:
            force_refresh: Bypass cache and fetch fresh metrics

        Returns:
            GPUMetrics with current GPU state
        """
        # Check cache
        now = time.time()
        if not force_refresh and self._cached_metrics:
            if (now - self._cache_timestamp) < self._cache_ttl:
                return self._cached_metrics

        # Check if nvidia-smi is available
        if not self._check_nvidia_smi():
            metrics = GPUMetrics(
                available=False,
                gpu_count=0,
                gpus=[],
                timestamp=datetime.utcnow(),
                error="nvidia-smi not available",
            )
            self._cached_metrics = metrics
            self._cache_timestamp = now
            return metrics

        # Fetch fresh metrics
        try:
            metrics = await self._fetch_nvidia_smi_metrics()
            self._cached_metrics = metrics
            self._cache_timestamp = now
            return metrics
        except Exception as e:
            logger.error(f"Failed to fetch GPU metrics: {e}")
            return GPUMetrics(
                available=False, gpu_count=0, gpus=[], timestamp=datetime.utcnow(), error=str(e)
            )

    async def _fetch_nvidia_smi_metrics(self) -> GPUMetrics:
        """Fetch metrics using nvidia-smi."""
        # Query format: index, name, driver, memory.total, memory.used, memory.free,
        #               utilization.gpu, utilization.memory, temperature.gpu,
        #               power.draw, power.limit
        query_format = (
            "index,name,driver_version,memory.total,memory.used,memory.free,"
            "utilization.gpu,utilization.memory,temperature.gpu,"
            "power.draw,power.limit"
        )

        cmd = ["nvidia-smi", f"--query-gpu={query_format}", "--format=csv,noheader,nounits"]

        # Run nvidia-smi asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode().strip() if stderr else "nvidia-smi failed"
            raise RuntimeError(error_msg)

        # Parse output
        gpus = []
        output = stdout.decode().strip()

        # Get CUDA version separately
        cuda_version = await self._get_cuda_version()

        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 11:
                continue

            try:
                gpu = GPUInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    driver_version=parts[2],
                    cuda_version=cuda_version,
                    memory_total_mb=int(parts[3]),
                    memory_used_mb=int(parts[4]),
                    memory_free_mb=int(parts[5]),
                    utilization_gpu=int(parts[6]) if parts[6] != "[Not Supported]" else 0,
                    utilization_memory=int(parts[7]) if parts[7] != "[Not Supported]" else 0,
                    temperature_gpu=int(parts[8]) if parts[8] != "[Not Supported]" else 0,
                    power_draw_w=float(parts[9]) if parts[9] != "[Not Supported]" else 0.0,
                    power_limit_w=float(parts[10]) if parts[10] != "[Not Supported]" else 0.0,
                )
                gpus.append(gpu)
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse GPU info: {e}")
                continue

        return GPUMetrics(
            available=True,
            gpu_count=len(gpus),
            gpus=gpus,
            timestamp=datetime.utcnow(),
        )

    async def _get_cuda_version(self) -> str:
        """Get CUDA version from nvidia-smi."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "nvidia-smi",
                "--query-gpu=driver_version",
                "--format=csv,noheader",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()

            # Try to get CUDA version from nvidia-smi output
            proc2 = await asyncio.create_subprocess_exec(
                "nvidia-smi", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout2, _ = await proc2.communicate()
            output = stdout2.decode()

            # Parse CUDA Version from nvidia-smi header
            for line in output.split("\n"):
                if "CUDA Version" in line:
                    # Format: "| NVIDIA-SMI 535.154.05   Driver Version: 535.154.05   CUDA Version: 12.2     |"
                    parts = line.split("CUDA Version:")
                    if len(parts) > 1:
                        return parts[1].strip().rstrip("|").strip()

            return "Unknown"
        except Exception:
            return "Unknown"

    def get_prometheus_metrics(self, metrics: GPUMetrics) -> str:
        """
        Generate Prometheus/OpenMetrics format output for GPU metrics.

        Args:
            metrics: GPUMetrics to export

        Returns:
            String in Prometheus exposition format
        """
        lines = []

        # GPU availability
        lines.append("# HELP ollama_gpu_available Whether GPU is available (1=yes, 0=no)")
        lines.append("# TYPE ollama_gpu_available gauge")
        lines.append(f"ollama_gpu_available {1 if metrics.available else 0}")

        if not metrics.available:
            return "\n".join(lines)

        # GPU count
        lines.append("# HELP ollama_gpu_count Number of GPUs available")
        lines.append("# TYPE ollama_gpu_count gauge")
        lines.append(f"ollama_gpu_count {metrics.gpu_count}")

        # Per-GPU metrics
        for gpu in metrics.gpus:
            labels = f'gpu="{gpu.index}",name="{gpu.name}"'

            # Memory metrics
            lines.append("# HELP ollama_gpu_memory_total_bytes Total GPU memory in bytes")
            lines.append("# TYPE ollama_gpu_memory_total_bytes gauge")
            lines.append(
                f"ollama_gpu_memory_total_bytes{{{labels}}} {gpu.memory_total_mb * 1024 * 1024}"
            )

            lines.append("# HELP ollama_gpu_memory_used_bytes Used GPU memory in bytes")
            lines.append("# TYPE ollama_gpu_memory_used_bytes gauge")
            lines.append(
                f"ollama_gpu_memory_used_bytes{{{labels}}} {gpu.memory_used_mb * 1024 * 1024}"
            )

            # Utilization
            lines.append("# HELP ollama_gpu_utilization_percent GPU utilization percentage")
            lines.append("# TYPE ollama_gpu_utilization_percent gauge")
            lines.append(f"ollama_gpu_utilization_percent{{{labels}}} {gpu.utilization_gpu}")

            # Temperature
            lines.append("# HELP ollama_gpu_temperature_celsius GPU temperature in Celsius")
            lines.append("# TYPE ollama_gpu_temperature_celsius gauge")
            lines.append(f"ollama_gpu_temperature_celsius{{{labels}}} {gpu.temperature_gpu}")

            # Power
            lines.append("# HELP ollama_gpu_power_draw_watts Current power draw in watts")
            lines.append("# TYPE ollama_gpu_power_draw_watts gauge")
            lines.append(f"ollama_gpu_power_draw_watts{{{labels}}} {gpu.power_draw_w}")

        return "\n".join(lines)


# Global GPU monitor instance
_gpu_monitor: GPUMonitor | None = None


def get_gpu_monitor() -> GPUMonitor:
    """Get the global GPU monitor instance."""
    global _gpu_monitor
    if _gpu_monitor is None:
        _gpu_monitor = GPUMonitor()
    return _gpu_monitor


@dataclass
class SystemMetrics:
    """System CPU and RAM metrics."""

    cpu_percent: float = 0.0
    cpu_count: int = 0
    cpu_count_logical: int = 0
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_available_gb: float = 0.0
    memory_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None
    available: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "available": self.available,
            "cpu_percent": round(self.cpu_percent, 1),
            "cpu_count": self.cpu_count,
            "cpu_count_logical": self.cpu_count_logical,
            "memory_total_gb": round(self.memory_total_gb, 2),
            "memory_used_gb": round(self.memory_used_gb, 2),
            "memory_available_gb": round(self.memory_available_gb, 2),
            "memory_percent": round(self.memory_percent, 1),
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


class SystemMonitor:
    """
    Monitor system CPU and RAM metrics using psutil.

    Supports caching to avoid excessive system calls.
    """

    def __init__(self, cache_ttl_seconds: float = 2.0):
        """
        Initialize system monitor.

        Args:
            cache_ttl_seconds: How long to cache metrics (default 2s)
        """
        self._cache_ttl = cache_ttl_seconds
        self._cached_metrics: SystemMetrics | None = None
        self._cache_timestamp: float = 0

    def get_metrics(self, force_refresh: bool = False) -> SystemMetrics:
        """
        Get current system metrics.

        Args:
            force_refresh: Bypass cache and fetch fresh metrics

        Returns:
            SystemMetrics with current CPU and RAM state
        """
        # Check cache
        now = time.time()
        if not force_refresh and self._cached_metrics:
            if (now - self._cache_timestamp) < self._cache_ttl:
                return self._cached_metrics

        # Check if psutil is available
        if not PSUTIL_AVAILABLE:
            metrics = SystemMetrics(available=False, error="psutil not available")
            self._cached_metrics = metrics
            self._cache_timestamp = now
            return metrics

        # Fetch fresh metrics
        try:
            metrics = self._fetch_system_metrics()
            self._cached_metrics = metrics
            self._cache_timestamp = now
            return metrics
        except Exception as e:
            logger.error(f"Failed to fetch system metrics: {e}")
            return SystemMetrics(available=False, error=str(e))

    def _fetch_system_metrics(self) -> SystemMetrics:
        """Fetch metrics using psutil."""
        memory = psutil.virtual_memory()

        return SystemMetrics(
            available=True,
            cpu_percent=psutil.cpu_percent(interval=0.1),
            cpu_count=psutil.cpu_count(logical=False) or 0,
            cpu_count_logical=psutil.cpu_count(logical=True) or 0,
            memory_total_gb=memory.total / (1024**3),
            memory_used_gb=memory.used / (1024**3),
            memory_available_gb=memory.available / (1024**3),
            memory_percent=memory.percent,
            timestamp=datetime.utcnow(),
        )

    def get_prometheus_metrics(self, metrics: SystemMetrics) -> str:
        """
        Generate Prometheus/OpenMetrics format output for system metrics.

        Args:
            metrics: SystemMetrics to export

        Returns:
            String in Prometheus exposition format
        """
        lines = []

        # CPU metrics
        lines.append("# HELP ollama_system_cpu_percent CPU usage percentage")
        lines.append("# TYPE ollama_system_cpu_percent gauge")
        lines.append(f"ollama_system_cpu_percent {metrics.cpu_percent}")

        lines.append("# HELP ollama_system_cpu_count Number of CPU cores")
        lines.append("# TYPE ollama_system_cpu_count gauge")
        lines.append(f"ollama_system_cpu_count {metrics.cpu_count}")

        # Memory metrics
        lines.append("# HELP ollama_system_memory_total_bytes Total system memory in bytes")
        lines.append("# TYPE ollama_system_memory_total_bytes gauge")
        lines.append(
            f"ollama_system_memory_total_bytes {int(metrics.memory_total_gb * 1024 * 1024 * 1024)}"
        )

        lines.append("# HELP ollama_system_memory_used_bytes Used system memory in bytes")
        lines.append("# TYPE ollama_system_memory_used_bytes gauge")
        lines.append(
            f"ollama_system_memory_used_bytes {int(metrics.memory_used_gb * 1024 * 1024 * 1024)}"
        )

        lines.append("# HELP ollama_system_memory_percent Memory usage percentage")
        lines.append("# TYPE ollama_system_memory_percent gauge")
        lines.append(f"ollama_system_memory_percent {metrics.memory_percent}")

        return "\n".join(lines)


# Global system monitor instance
_system_monitor: SystemMonitor | None = None


def get_system_monitor() -> SystemMonitor:
    """Get the global system monitor instance."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


@dataclass
class SystemMetricsSnapshot:
    """Single snapshot of system metrics for history."""

    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    gpu_available: bool
    gpu_utilization_percent: float
    vram_used_gb: float
    vram_total_gb: float
    gpu_temperature_celsius: float
    queue_depth: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": round(self.cpu_percent, 1),
            "memory_percent": round(self.memory_percent, 1),
            "memory_used_gb": round(self.memory_used_gb, 2),
            "memory_total_gb": round(self.memory_total_gb, 2),
            "gpu_available": self.gpu_available,
            "gpu_utilization_percent": round(self.gpu_utilization_percent, 1),
            "vram_used_gb": round(self.vram_used_gb, 2),
            "vram_total_gb": round(self.vram_total_gb, 2),
            "gpu_temperature_celsius": round(self.gpu_temperature_celsius, 1),
            "queue_depth": self.queue_depth,
        }


class SystemMetricsHistory:
    """
    Stores historical system metrics for time-series visualization.

    Maintains a rolling window of metrics snapshots.
    """

    def __init__(self, max_snapshots: int = 3600):
        """
        Initialize history storage.

        Args:
            max_snapshots: Maximum number of snapshots to store (default 1 hour at 1/sec)
        """
        from collections import deque

        self._snapshots: deque = deque(maxlen=max_snapshots)
        self._lock = Lock()
        self._collection_interval = 5  # seconds between snapshots
        self._running = False
        self._task: asyncio.Task | None = None

    def add_snapshot(self, snapshot: SystemMetricsSnapshot) -> None:
        """Add a metrics snapshot to history."""
        with self._lock:
            self._snapshots.append(snapshot)

    def get_history(
        self, time_range_seconds: int = 3600, max_points: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get historical metrics.

        Args:
            time_range_seconds: How far back to look (default 1 hour)
            max_points: Maximum number of data points to return

        Returns:
            List of metric snapshots
        """
        with self._lock:
            if not self._snapshots:
                return []

            cutoff = datetime.utcnow() - timedelta(seconds=time_range_seconds)
            filtered = [s for s in self._snapshots if s.timestamp > cutoff]

            # Downsample if too many points
            if len(filtered) > max_points:
                step = len(filtered) // max_points
                filtered = filtered[::step]

            return [s.to_dict() for s in filtered]

    async def start_collection(
        self, gpu_monitor: GPUMonitor, system_monitor: SystemMonitor, metrics_collector_getter
    ) -> None:
        """
        Start background collection of metrics.

        Args:
            gpu_monitor: GPU monitor instance
            system_monitor: System monitor instance
            metrics_collector_getter: Callable to get metrics collector
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(
            self._collection_loop(gpu_monitor, system_monitor, metrics_collector_getter)
        )
        logger.info("Started system metrics history collection")

    async def stop_collection(self) -> None:
        """Stop background collection."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Expected when cancelling the task
        logger.info("Stopped system metrics history collection")

    async def _collection_loop(
        self, gpu_monitor: GPUMonitor, system_monitor: SystemMonitor, metrics_collector_getter
    ) -> None:
        """Background loop to collect metrics."""
        while self._running:
            try:
                # Get current metrics
                gpu_metrics = await gpu_monitor.get_metrics()
                system_metrics = system_monitor.get_metrics()

                # Get queue depth from metrics collector
                queue_depth = 0
                try:
                    collector = metrics_collector_getter()
                    queue_depth = collector.get_queue_depth()
                except Exception:
                    pass  # Metrics collector may not be available yet

                # Create snapshot
                snapshot = SystemMetricsSnapshot(
                    timestamp=datetime.utcnow(),
                    cpu_percent=system_metrics.cpu_percent,
                    memory_percent=system_metrics.memory_percent,
                    memory_used_gb=system_metrics.memory_used_gb,
                    memory_total_gb=system_metrics.memory_total_gb,
                    gpu_available=gpu_metrics.available,
                    gpu_utilization_percent=gpu_metrics.avg_gpu_utilization,
                    vram_used_gb=gpu_metrics.used_vram_gb,
                    vram_total_gb=gpu_metrics.total_vram_gb,
                    gpu_temperature_celsius=gpu_metrics.avg_temperature,
                    queue_depth=queue_depth,
                )

                self.add_snapshot(snapshot)

            except Exception as e:
                logger.warning(f"Failed to collect system metrics snapshot: {e}")

            await asyncio.sleep(self._collection_interval)


# Global system metrics history instance
_system_metrics_history: SystemMetricsHistory | None = None


def get_system_metrics_history() -> SystemMetricsHistory:
    """Get the global system metrics history instance."""
    global _system_metrics_history
    if _system_metrics_history is None:
        _system_metrics_history = SystemMetricsHistory()
    return _system_metrics_history
