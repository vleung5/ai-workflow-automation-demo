"""Async processing pipeline for workflow automation"""
import asyncio
import csv
import io
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from models import ProcessedRecord, JobResult, ValidationResult, RecordClassification, PriorityLevel, SentimentType, JobStatus
from src.config import config

logger = logging.getLogger(__name__)

class WorkflowProcessor:
    """Main processing pipeline for workflow automation"""
    
    def __init__(self):
        self.jobs: Dict[str, JobResult] = {}
        self.processing_queue: asyncio.Queue = None
        
    async def initialize(self):
        """Initialize the processor"""
        self.processing_queue = asyncio.Queue(maxsize=config.QUEUE_MAX_SIZE)
    
    async def validate_record(self, record: Dict[str, Any], record_id: int) -> ValidationResult:
        """Validate a CSV record"""
        errors = []
        warnings = []
        
        required_fields = ["description", "category", "priority"]
        for field in required_fields:
            if field not in record or not str(record[field]).strip():
                errors.append(f"Missing required field: {field}")
        
        desc = str(record.get("description", "")).strip()
        if len(desc) < 5:
            errors.append("Description too short (minimum 5 characters)")
        elif len(desc) > 500:
            warnings.append("Description is very long (>500 chars)")
        
        valid_categories = ["inquiry", "complaint", "feedback", "request", "issue"]
        if record.get("category", "").lower() not in valid_categories:
            warnings.append(f"Unknown category: {record.get('category')}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def classify_record(self, record: Dict[str, Any]) -> RecordClassification:
        """AI classification using keyword matching"""
        description = str(record.get("description", "")).lower()
        
        priority = PriorityLevel.NORMAL
        for level, keywords in config.PRIORITY_KEYWORDS.items():
            if any(keyword in description for keyword in keywords):
                priority = PriorityLevel(level)
                break
        
        positive_words = ["great", "excellent", "thanks", "appreciate", "happy", "satisfied"]
        negative_words = ["terrible", "bad", "angry", "disappointed", "broken", "issue"]
        
        positive_count = sum(1 for word in positive_words if word in description)
        negative_count = sum(1 for word in negative_words if word in description)
        
        if negative_count > positive_count:
            sentiment = SentimentType.NEGATIVE
            confidence = min(0.95, 0.6 + (negative_count * 0.1))
        elif positive_count > negative_count:
            sentiment = SentimentType.POSITIVE
            confidence = min(0.95, 0.6 + (positive_count * 0.1))
        else:
            sentiment = SentimentType.NEUTRAL
            confidence = 0.7
        
        category = record.get("category", "inquiry").lower()
        if category not in ["inquiry", "complaint", "feedback", "request", "issue"]:
            category = "inquiry"
        
        return RecordClassification(priority=priority, confidence=float(confidence), sentiment=sentiment, category=category)
    
    def generate_summary(self, record: Dict[str, Any], classification: RecordClassification) -> str:
        """Generate AI summary of the record"""
        description = str(record.get("description", "")).strip()
        summary_base = description.split(".")[0][:100]
        summary = f"[{classification.priority.upper()}] {summary_base}"
        
        if classification.sentiment == SentimentType.NEGATIVE:
            summary += " (⚠️ Negative feedback)"
        elif classification.sentiment == SentimentType.POSITIVE:
            summary += " (✓ Positive)"
        
        return summary
    
    async def process_record(self, record: Dict[str, Any], record_id: int) -> Optional[ProcessedRecord]:
        """Process a single record through the pipeline"""
        start_time = time.time()
        
        try:
            validation = await self.validate_record(record, record_id)
            classification = self.classify_record(record)
            summary = self.generate_summary(record, classification)
            processing_time_ms = (time.time() - start_time) * 1000
            
            return ProcessedRecord(
                id=record_id,
                original_data=record,
                validation=validation,
                classification=classification,
                summary=summary,
                processing_time_ms=processing_time_ms
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
            started_at=datetime.now()
        )
        
        self.jobs[job_id] = job
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content))
            records = list(reader)
            job.total_records = len(records)
            
            semaphore = asyncio.Semaphore(config.MAX_WORKERS)
            
            async def process_with_semaphore(idx: int, record: Dict[str, Any]):
                async with semaphore:
                    return await self.process_record(record, idx + 1)
            
            tasks = [process_with_semaphore(idx, record) for idx, record in enumerate(records)]
            processed = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in processed:
                if result and not isinstance(result, Exception):
                    job.results.append(result)
                    job.processed_records += 1
                else:
                    job.failed_records += 1
            
            job.statistics = self._calculate_statistics(job.results)
            job.status = JobStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
        
        job.completed_at = datetime.now()
        return job
    
    def _calculate_statistics(self, results: List[ProcessedRecord]) -> Dict[str, Any]:
        """Calculate aggregate statistics"""
        if not results:
            return {}
        
        priorities = {}
        sentiments = {}
        avg_confidence = 0
        total_time = 0
        
        for result in results:
            priority = result.classification.priority.value
            sentiment = result.classification.sentiment.value
            priorities[priority] = priorities.get(priority, 0) + 1
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
            avg_confidence += result.classification.confidence
            total_time += result.processing_time_ms
        
        return {
            "priorities": priorities,
            "sentiments": sentiments,
            "average_confidence": avg_confidence / len(results),
            "total_processing_time_ms": total_time,
            "avg_time_per_record_ms": total_time / len(results),
            "validation_errors": sum(len(r.validation.errors) for r in results),
            "validation_warnings": sum(len(r.validation.warnings) for r in results)
        }
    
    def get_job_status(self, job_id: str) -> Optional[JobResult]:
        """Retrieve job status"""
        return self.jobs.get(job_id)

processor = WorkflowProcessor()
