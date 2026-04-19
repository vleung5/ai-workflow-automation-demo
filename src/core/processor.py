"""CSV processing orchestration - decoupled from FastAPI"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.models.enums import JobStatus
from src.models.schemas import ProcessedRecord, JobResult
from src.core.validator import validate_record
from src.core.classifier import classify_record, generate_summary
from src.utils.csv_parser import parse_csv_content
from src.config import config

logger = logging.getLogger(__name__)


class WorkflowProcessor:
    """Main processing pipeline for workflow automation"""

    def __init__(self):
        self.jobs: Dict[str, JobResult] = {}
        self.processing_queue: Optional[asyncio.Queue] = None

    async def initialize(self):
        """Initialize the processor"""
        self.processing_queue = asyncio.Queue(maxsize=config.QUEUE_MAX_SIZE)

    async def process_record(
        self, record: Dict[str, Any], record_id: int
    ) -> Optional[ProcessedRecord]:
        """Process a single record through the pipeline"""
        start_time = time.time()
        try:
            validation = validate_record(record, record_id)
            classification = classify_record(record)
            summary = generate_summary(record, classification)
            processing_time_ms = (time.time() - start_time) * 1000

            return ProcessedRecord(
                id=record_id,
                original_data=record,
                validation=validation,
                classification=classification,
                summary=summary,
                processing_time_ms=processing_time_ms,
            )
        except Exception as e:
            logger.error(f"Error processing record {record_id}: {str(e)}")
            return None

    async def process_csv_data(self, csv_content: str, job_id: str) -> JobResult:
        """Process entire CSV file through the pipeline"""
        job = JobResult(
            job_id=job_id,
            status=JobStatus.PROCESSING,
            total_records=0,
            processed_records=0,
            failed_records=0,
            results=[],
            started_at=datetime.now(),
        )
        self.jobs[job_id] = job

        try:
            records, parse_errors = parse_csv_content(csv_content)
            if parse_errors:
                logger.warning(f"CSV parse warnings for job {job_id}: {parse_errors}")

            job.total_records = len(records)
            semaphore = asyncio.Semaphore(config.MAX_WORKERS)

            async def process_with_semaphore(idx: int, record: Dict[str, Any]):
                async with semaphore:
                    return await self.process_record(record, idx + 1)

            tasks = [process_with_semaphore(idx, rec) for idx, rec in enumerate(records)]
            processed = await asyncio.gather(*tasks, return_exceptions=True)

            for result in processed:
                if result and not isinstance(result, Exception):
                    job.results.append(result)
                    job.processed_records += 1
                else:
                    job.failed_records += 1

            job.statistics = _calculate_statistics(job.results)
            job.status = JobStatus.COMPLETED

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)

        job.completed_at = datetime.now()
        return job

    def get_job_status(self, job_id: str) -> Optional[JobResult]:
        """Retrieve job status"""
        return self.jobs.get(job_id)


def _calculate_statistics(results: List[ProcessedRecord]) -> Dict[str, Any]:
    """Calculate aggregate statistics from processed records"""
    if not results:
        return {}

    priorities: Dict[str, int] = {}
    sentiments: Dict[str, int] = {}
    avg_confidence = 0.0
    total_time = 0.0

    for result in results:
        priority = result.classification.priority.value
        sentiment = result.classification.sentiment.value
        priorities[priority] = priorities.get(priority, 0) + 1
        sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        avg_confidence += result.classification.confidence
        total_time += result.processing_time_ms

    n = len(results)
    return {
        "priorities": priorities,
        "sentiments": sentiments,
        "average_confidence": avg_confidence / n,
        "total_processing_time_ms": total_time,
        "avg_time_per_record_ms": total_time / n,
        "validation_errors": sum(len(r.validation.errors) for r in results),
        "validation_warnings": sum(len(r.validation.warnings) for r in results),
    }


# Module-level singleton used by API routes and queue workers
processor = WorkflowProcessor()
