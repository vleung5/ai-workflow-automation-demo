"""
Custom Datadog monitoring and alerting for AI Workflow Automation
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from datadog_config import send_datadog_metric, send_datadog_event, get_datadog_tags

logger = logging.getLogger(__name__)


class WorkflowMonitor:
    """Monitor workflow metrics and send to Datadog"""
    
    def __init__(self):
        self.job_times = {}
        self.s3_operations = {
            "read": 0,
            "write": 0,
            "delete": 0,
            "failed": 0
        }
        self.processing_stats = {
            "total_records": 0,
            "successful_records": 0,
            "failed_records": 0
        }
    
    def track_job_start(self, job_id: str):
        """Track job start time"""
        self.job_times[job_id] = {
            "start_time": time.time(),
            "status": "processing"
        }
    
    def track_job_end(self, job_id: str, status: str, records_processed: int = 0):
        """Track job completion and send metrics"""
        
        if job_id not in self.job_times:
            return
        
        job_info = self.job_times[job_id]
        duration = time.time() - job_info["start_time"]
        
        # Send duration metric
        send_datadog_metric(
            "job.duration",
            duration,
            "gauge",
            {
                "job_id": job_id,
                "status": status
            }
        )
        
        # Send records processed metric
        if records_processed > 0:
            throughput = records_processed / duration if duration > 0 else 0
            send_datadog_metric(
                "job.throughput",
                throughput,
                "gauge",
                {
                    "job_id": job_id,
                    "unit": "records_per_second"
                }
            )
        
        # Send completion event
        alert_type = "success" if status == "completed" else "error"
        send_datadog_event(
            title=f"Job {status.title()}",
            text=f"Job {job_id} {status} in {duration:.2f}s",
            alert_type=alert_type,
            tags=["job", status]
        )
        
        # Update tracking
        self.job_times[job_id]["end_time"] = time.time()
        self.job_times[job_id]["status"] = status
        self.job_times[job_id]["duration"] = duration
    
    def track_s3_operation(self, operation: str, success: bool = True, duration: float = 0):
        """Track S3 operations"""
        
        if not success:
            self.s3_operations["failed"] += 1
            send_datadog_metric("s3.operation.failed", 1, "increment")
        else:
            self.s3_operations[operation] = self.s3_operations.get(operation, 0) + 1
            send_datadog_metric(f"s3.operation.{operation}", 1, "increment")
            
            if duration > 0:
                send_datadog_metric(
                    f"s3.operation.{operation}.duration",
                    duration,
                    "gauge"
                )
    
    def track_record_processing(self, total: int, successful: int, failed: int):
        """Track record processing statistics"""
        
        self.processing_stats["total_records"] += total
        self.processing_stats["successful_records"] += successful
        self.processing_stats["failed_records"] += failed
        
        send_datadog_metric(
            "records.total",
            self.processing_stats["total_records"],
            "gauge"
        )
        
        send_datadog_metric(
            "records.successful",
            self.processing_stats["successful_records"],
            "gauge"
        )
        
        send_datadog_metric(
            "records.failed",
            self.processing_stats["failed_records"],
            "gauge"
        )
        
        if total > 0:
            success_rate = (successful / total) * 100
            send_datadog_metric(
                "records.success_rate",
                success_rate,
                "gauge"
            )
    
    def send_health_check(self, service_name: str, status: str, details: Dict[str, Any] = None):
        """Send health check to Datadog"""
        
        alert_type = "success" if status == "healthy" else "warning"
        
        text = f"{service_name} is {status}"
        if details:
            text += f"\nDetails: {details}"
        
        send_datadog_event(
            title=f"{service_name} Health Check",
            text=text,
            alert_type=alert_type,
            tags=["health", "monitoring"]
        )
    
    def get_job_metrics(self) -> Dict[str, Any]:
        """Get aggregated job metrics"""
        
        if not self.job_times:
            return {}
        
        completed_jobs = [j for j in self.job_times.values() if j.get("status") == "completed"]
        failed_jobs = [j for j in self.job_times.values() if j.get("status") == "failed"]
        
        if completed_jobs:
            avg_duration = sum(j.get("duration", 0) for j in completed_jobs) / len(completed_jobs)
        else:
            avg_duration = 0
        
        return {
            "total_jobs": len(self.job_times),
            "completed_jobs": len(completed_jobs),
            "failed_jobs": len(failed_jobs),
            "average_duration": avg_duration,
            "success_rate": (len(completed_jobs) / len(self.job_times) * 100) if self.job_times else 0
        }
    
    def send_summary_report(self):
        """Send summary report to Datadog"""
        
        metrics = self.get_job_metrics()
        
        if not metrics:
            return
        
        summary_text = f"""
        Jobs Summary:
        - Total Jobs: {metrics['total_jobs']}
        - Completed: {metrics['completed_jobs']}
        - Failed: {metrics['failed_jobs']}
        - Average Duration: {metrics['average_duration']:.2f}s
        - Success Rate: {metrics['success_rate']:.1f}%
        
        Records Summary:
        - Total: {self.processing_stats['total_records']}
        - Successful: {self.processing_stats['successful_records']}
        - Failed: {self.processing_stats['failed_records']}
        """
        
        send_datadog_event(
            title="Workflow Summary Report",
            text=summary_text,
            alert_type="info",
            tags=["summary", "report"]
        )


# Global monitor instance
workflow_monitor = WorkflowMonitor()


def get_workflow_monitor() -> WorkflowMonitor:
    """Get the global workflow monitor instance"""
    return workflow_monitor
