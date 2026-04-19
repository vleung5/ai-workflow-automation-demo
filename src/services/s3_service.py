"""S3 service - polling and file management"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class S3PollingService:
    """Service for polling and reading files from S3 bucket"""

    def __init__(self, bucket_name: str, prefix: str = "incoming/", region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.region = region
        self.processed_files: set = set()
        self.polling_interval = 30
        self.is_running = False

        try:
            import boto3

            self.s3_client = boto3.client("s3", region_name=region)
            self.s3_resource = boto3.resource("s3", region_name=region)
            logger.info(f"S3 client initialized for bucket: {bucket_name}")
        except ImportError:
            logger.error("boto3 not installed. Install it with: pip install boto3")
            self.s3_client = None
            self.s3_resource = None

    async def get_pending_files(self) -> List[Dict[str, Any]]:
        """Get list of unprocessed CSV files from S3"""
        if not self.s3_client:
            return []
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=self.prefix, MaxKeys=100
            )
            files = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/") or key in self.processed_files:
                    continue
                if key.lower().endswith(".csv"):
                    files.append(
                        {
                            "key": key,
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"],
                            "etag": obj["ETag"],
                        }
                    )
            logger.info(f"Found {len(files)} pending files in S3")
            return files
        except Exception as e:
            logger.error(f"Error listing S3 files: {str(e)}")
            return []

    async def read_file_from_s3(self, file_key: str) -> Optional[str]:
        """Read CSV file content from S3"""
        if not self.s3_client:
            return None
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            content = response["Body"].read().decode("utf-8")
            logger.info(f"Read {len(content)} bytes from s3://{self.bucket_name}/{file_key}")
            return content
        except Exception as e:
            logger.error(f"Error reading {file_key} from S3: {str(e)}")
            return None

    async def mark_file_as_processed(self, file_key: str, status: str = "success") -> bool:
        """Move file to processed/failed folder"""
        if not self.s3_client:
            return False
        try:
            dest_prefix = "processed/" if status == "success" else f"{status}/"
            filename = file_key.split("/")[-1]
            dest_key = f"{dest_prefix}{datetime.now().strftime('%Y-%m-%d')}/{filename}"
            self.s3_client.copy_object(
                CopySource={"Bucket": self.bucket_name, "Key": file_key},
                Bucket=self.bucket_name,
                Key=dest_key,
            )
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            self.processed_files.add(file_key)
            logger.info(f"File {file_key} moved to {dest_key}")
            return True
        except Exception as e:
            logger.error(f"Error moving file {file_key}: {str(e)}")
            return False

    async def upload_results_to_s3(self, results: Dict[str, Any], job_id: str) -> Optional[str]:
        """Upload processing results JSON to S3"""
        if not self.s3_client:
            return None
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            results_key = f"results/{timestamp}/{job_id}_results.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=results_key,
                Body=json.dumps(results, default=str, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            logger.info(f"Results uploaded to s3://{self.bucket_name}/{results_key}")
            return results_key
        except Exception as e:
            logger.error(f"Error uploading results to S3: {str(e)}")
            return None

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Return S3 polling statistics"""
        pending = await self.get_pending_files()
        return {
            "bucket": self.bucket_name,
            "prefix": self.prefix,
            "pending_files": len(pending),
            "processed_files": len(self.processed_files),
            "is_running": self.is_running,
            "polling_interval_seconds": self.polling_interval,
            "timestamp": datetime.now().isoformat(),
        }

    async def start_polling(self, processor, callback=None):
        """Start polling S3 bucket for new files"""
        self.is_running = True
        logger.info(f"Starting S3 polling (interval: {self.polling_interval}s)")

        while self.is_running:
            try:
                pending_files = await self.get_pending_files()
                for file_info in pending_files:
                    file_key = file_info["key"]
                    try:
                        csv_content = await self.read_file_from_s3(file_key)
                        if csv_content:
                            job_id = file_key.replace("/", "_").replace(".csv", "")
                            job_result = await processor.process_csv_data(csv_content, job_id)
                            results_key = await self.upload_results_to_s3(job_result.dict(), job_id)
                            await self.mark_file_as_processed(file_key, "success")
                            if callback:
                                await callback(job_id, "success", results_key)
                        else:
                            await self.mark_file_as_processed(file_key, "failed")
                            if callback:
                                await callback(file_key, "failed", None)
                    except Exception as e:
                        logger.error(f"Error processing file {file_key}: {str(e)}")
                        await self.mark_file_as_processed(file_key, "failed")
                        if callback:
                            await callback(file_key, "error", str(e))
                await asyncio.sleep(self.polling_interval)
            except Exception as e:
                logger.error(f"Error in polling loop: {str(e)}")
                await asyncio.sleep(self.polling_interval)

    async def stop_polling(self):
        """Stop the polling service"""
        self.is_running = False
        logger.info("S3 polling stopped")


_s3_service: Optional[S3PollingService] = None


def initialize_s3_polling(
    bucket_name: str, prefix: str = "incoming/", region: str = "us-east-1"
) -> S3PollingService:
    global _s3_service
    _s3_service = S3PollingService(bucket_name, prefix, region)
    return _s3_service


def get_s3_polling_service() -> Optional[S3PollingService]:
    return _s3_service
