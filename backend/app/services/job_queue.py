"""
VARUNA Asynchronous Job & Pipeline Execution System.
SIH 2026 Problem Statement: SIH26081

Provides background execution for long-running workflows:
- Dataset Ingestion
- Benchmark Experiments
- Continuous Verification Cycles
- Model Recalibration / Retraining

Architecture:
- In-memory bounded worker pool for local / zero-dependency development
- Standard task submission interface easily swappable with Celery / Redis in enterprise deployments
- Thread-safe job state tracking with progress percentage and error reporting
"""

import uuid
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import logging

logger = logging.getLogger("varuna-job-queue")


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobRecord:
    def __init__(self, job_id: str, job_type: str, metadata: Optional[Dict[str, Any]] = None):
        self.job_id = job_id
        self.job_type = job_type
        self.status = JobStatus.QUEUED
        self.progress_pct = 0.0
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "progress_pct": round(self.progress_pct, 1),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": round((self.completed_at - self.started_at).total_seconds(), 2) if (self.completed_at and self.started_at) else None,
            "result": self.result,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class JobQueueManager:
    """Manages asynchronous pipeline jobs."""

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="varuna-worker")
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = Lock()

    def submit_job(
        self,
        job_type: str,
        target_fn: Callable[..., Dict[str, Any]],
        *args,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        job_id = f"JOB_{job_type.upper()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        record = JobRecord(job_id=job_id, job_type=job_type, metadata=metadata)

        with self._lock:
            self._jobs[job_id] = record

        def _runner():
            with self._lock:
                record.status = JobStatus.RUNNING
                record.started_at = datetime.now(timezone.utc)
                record.progress_pct = 10.0

            try:
                logger.info(f"Starting background job {job_id} ({job_type})...")
                res = target_fn(*args, **kwargs)
                with self._lock:
                    record.status = JobStatus.COMPLETED
                    record.progress_pct = 100.0
                    record.completed_at = datetime.now(timezone.utc)
                    record.result = res
                logger.info(f"Background job {job_id} completed successfully.")
            except Exception as e:
                logger.error(f"Background job {job_id} failed: {e}", exc_info=True)
                with self._lock:
                    record.status = JobStatus.FAILED
                    record.completed_at = datetime.now(timezone.utc)
                    record.error_message = str(e)

        self._executor.submit(_runner)
        return job_id

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._jobs.values())
        items.sort(key=lambda x: x.created_at, reverse=True)
        return [item.to_dict() for item in items[:limit]]

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec and rec.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                rec.status = JobStatus.CANCELLED
                rec.completed_at = datetime.now(timezone.utc)
                return True
        return False


job_queue = JobQueueManager()
