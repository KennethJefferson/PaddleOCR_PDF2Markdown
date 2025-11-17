"""
Job queue manager for PDF processing tasks.

Handles job submission, status tracking, and sequential processing
using an in-memory queue.
"""

import queue
import threading
import uuid
import logging
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a PDF processing job."""
    job_id: str
    filename: str
    pdf_data: bytes
    status: JobStatus = JobStatus.QUEUED
    markdown_result: Optional[str] = None
    image_paths: Optional[List[str]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert job to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "filename": self.filename,
            "status": self.status.value,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "has_result": self.markdown_result is not None,
        }


class QueueManager:
    """Manages job queue and worker thread for PDF processing."""

    def __init__(self, pdf_processor, num_workers: int = 1):
        """
        Initialize the queue manager.

        Args:
            pdf_processor: PDFProcessor instance
            num_workers: Number of worker threads (default: 1)
        """
        self.pdf_processor = pdf_processor
        self.num_workers = num_workers

        # Job queue and storage
        self.job_queue = queue.Queue()
        self.jobs: Dict[str, Job] = {}  # job_id -> Job
        self.lock = threading.Lock()

        # Worker threads
        self.workers: List[threading.Thread] = []
        self.stop_event = threading.Event()

        logger.info(f"QueueManager initialized with {num_workers} worker(s)")

    def start(self):
        """Start worker threads."""
        logger.info("Starting worker threads...")
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker,
                name=f"Worker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        logger.info(f"Started {len(self.workers)} worker thread(s)")

    def stop(self):
        """Stop worker threads gracefully."""
        logger.info("Stopping workers...")
        self.stop_event.set()

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5.0)

        logger.info("Workers stopped")

    def submit_job(self, filename: str, pdf_data: bytes) -> str:
        """
        Submit a new PDF processing job.

        Args:
            filename: Original filename of the PDF
            pdf_data: PDF file content as bytes

        Returns:
            job_id: Unique job identifier
        """
        job_id = str(uuid.uuid4())

        job = Job(
            job_id=job_id,
            filename=filename,
            pdf_data=pdf_data
        )

        with self.lock:
            self.jobs[job_id] = job

        self.job_queue.put(job_id)

        logger.info(f"Job submitted: {job_id} (filename: {filename})")
        return job_id

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get status of a job.

        Args:
            job_id: Job identifier

        Returns:
            Job status dict or None if not found
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                return job.to_dict()
        return None

    def get_job_result(self, job_id: str) -> Optional[Dict]:
        """
        Get result of a completed job.

        Args:
            job_id: Job identifier

        Returns:
            Dict with markdown and metadata, or None if not ready
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None

            if job.status == JobStatus.COMPLETED:
                return {
                    "job_id": job_id,
                    "filename": job.filename,
                    "markdown": job.markdown_result,
                    "image_count": len(job.image_paths) if job.image_paths else 0,
                    "completed_at": job.completed_at.isoformat()
                }
            elif job.status == JobStatus.FAILED:
                return {
                    "job_id": job_id,
                    "filename": job.filename,
                    "error": job.error,
                    "status": "failed"
                }

        return None

    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        with self.lock:
            queued = sum(1 for j in self.jobs.values() if j.status == JobStatus.QUEUED)
            processing = sum(1 for j in self.jobs.values() if j.status == JobStatus.PROCESSING)
            completed = sum(1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED)
            failed = sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED)

        return {
            "queue_size": self.job_queue.qsize(),
            "total_jobs": len(self.jobs),
            "queued": queued,
            "processing": processing,
            "completed": completed,
            "failed": failed,
        }

    def _worker(self):
        """Worker thread that processes jobs from the queue."""
        worker_name = threading.current_thread().name
        logger.info(f"{worker_name} started")

        while not self.stop_event.is_set():
            try:
                # Get job from queue with timeout
                try:
                    job_id = self.job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Get job object
                with self.lock:
                    job = self.jobs.get(job_id)

                if not job:
                    logger.error(f"{worker_name}: Job {job_id} not found")
                    continue

                # Update status to processing
                with self.lock:
                    job.status = JobStatus.PROCESSING
                    job.started_at = datetime.now()

                logger.info(f"{worker_name}: Processing job {job_id} ({job.filename})")

                # Process PDF
                try:
                    markdown_text, image_paths = self.pdf_processor.process_pdf(job.pdf_data)

                    # Update job with results
                    with self.lock:
                        job.status = JobStatus.COMPLETED
                        job.markdown_result = markdown_text
                        job.image_paths = image_paths
                        job.completed_at = datetime.now()

                    logger.info(f"{worker_name}: Completed job {job_id}")

                except Exception as e:
                    logger.error(f"{worker_name}: Failed to process job {job_id}: {e}")

                    # Update job with error
                    with self.lock:
                        job.status = JobStatus.FAILED
                        job.error = str(e)
                        job.completed_at = datetime.now()

                finally:
                    self.job_queue.task_done()

            except Exception as e:
                logger.error(f"{worker_name}: Unexpected error: {e}")

        logger.info(f"{worker_name} stopped")
