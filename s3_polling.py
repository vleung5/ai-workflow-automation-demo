"""
S3 polling service for workflow automation
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class S3PollingService:
    """Service for polling and reading files from S3 bucket"""
    
    def __init__(self, bucket_name: str, prefix: str = "incoming/", region: str = "us-east-1"):
        """
        Initialize S3 Polling Service
        
        Args:
            bucket_name: S3 bucket name
            prefix: S3 prefix to poll (default: "incoming/")
            region: AWS region (default: "us-east-1")
        """
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.region = region
        self.processed_files: set = set()
        self.polling_interval = 30  # seconds
        self.is_running = False
        
        try:
            import boto3
            self.s3_client = boto3.client('s3', region_name=region)
            self.s3_resource = boto3.resource('s3', region_name=region)
            logger.info(f"S3 client initialized for bucket: {bucket_name}")
        except ImportError:
            logger.error("boto3 not installed. Install it with: pip install boto3")
            self.s3_client = None
            self.s3_resource = None
    
    async def get_pending_files(self) -> List[Dict[str, Any]]:
        """Get list of unprocessed CSV files from S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix,
                MaxKeys=100
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('/') or obj['Key'] in self.processed_files:
                        continue
                    
                    if obj['Key'].lower().endswith('.csv'):
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'etag': obj['ETag']
                        })
            
            logger.info(f"Found {len(files)} pending files in S3")
            return files
            
        except Exception as e:
            logger.error(f"Error listing S3 files: {str(e)}")
            return []
    
    async def read_file_from_s3(self, file_key: str) -> Optional[str]:
        """Read CSV file content from S3"""
        if not self.s3_client:
            logger.error("S3 client not initialized")
            return None
        
        try:
            logger.info(f"Reading file from S3: {file_key}")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully read {len(content)} bytes from {file_key}")
            return content
            
        except Exception as e:
            logger.error(f"Error reading file {file_key} from S3: {str(e)}")
            return None
    
    async def mark_file_as_processed(self, file_key: str, status: str = "success") -> bool:
        """Move file to processed folder in S3"""
        if not self.s3_client:
            return False
        
        try:
            dest_prefix = "processed/" if status == "success" else f"{status}/"
            filename = file_key.split('/')[-1]
            dest_key = f"{dest_prefix}{datetime.now().strftime('%Y-%m-%d')}/{filename}"
            
            copy_source = {'Bucket': self.bucket_name, 'Key': file_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key
            )
            
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            self.processed_files.add(file_key)
            
            logger.info(f"File {file_key} moved to {dest_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {file_key}: {str(e)}")
            return False
    
    async def upload_results_to_s3(self, results: Dict[str, Any], job_id: str) -> Optional[str]:
        """Upload processing results to S3"""
        if not self.s3_client:
            return None
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            results_key = f"results/{timestamp}/{job_id}_results.json"
            
            results_json = json.dumps(results, default=str, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=results_key,
                Body=results_json.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"Results uploaded to S3: {results_key}")
            return results_key
            
        except Exception as e:
            logger.error(f"Error uploading results to S3: {str(e)}")
            return None
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get S3 polling statistics"""
        try:
            pending_files = await self.get_pending_files()
            
            return {
                'bucket': self.bucket_name,
                'prefix': self.prefix,
                'pending_files': len(pending_files),
                'processed_files': len(self.processed_files),
                'is_running': self.is_running,
                'polling_interval_seconds': self.polling_interval,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {}
    
    async def start_polling(self, processor, callback=None):
        """Start polling S3 bucket for new files"""
        self.is_running = True
        logger.info(f"Starting S3 polling (interval: {self.polling_interval}s)")
        
        while self.is_running:
            try:
                pending_files = await self.get_pending_files()
                
                if pending_files:
                    logger.info(f"Processing {len(pending_files)} files from S3")
                    
                    for file_info in pending_files:
                        file_key = file_info['key']
                        
                        try:
                            csv_content = await self.read_file_from_s3(file_key)
                            
                            if csv_content:
                                job_id = file_key.replace('/', '_').replace('.csv', '')
                                logger.info(f"Starting job {job_id} for file {file_key}")
                                
                                job_result = await processor.process_csv_data(csv_content, job_id)
                                results_key = await self.upload_results_to_s3(
                                    job_result.dict(),
                                    job_id
                                )
                                
                                await self.mark_file_as_processed(file_key, "success")
                                
                                if callback:
                                    await callback(job_id, "success", results_key)
                                
                                logger.info(f"Job {job_id} completed successfully")
                            else:
                                await self.mark_file_as_processed(file_key, "failed")
                                if callback:
                                    await callback(file_key, "failed", None)
                                
                        except Exception as e:
                            logger.error(f"Error processing file {file_key}: {str(e)}")
                            await self.mark_file_as_processed(file_key, "failed")
                            if callback:
                                await callback(file_key, "error", str(e))
                else:
                    logger.debug("No pending files to process")
                
                await asyncio.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {str(e)}")
                await asyncio.sleep(self.polling_interval)
    
    async def stop_polling(self):
        """Stop the polling service"""
        self.is_running = False
        logger.info("S3 polling stopped")
    
    async def create_sample_file(self, filename: str = "sample_input.csv") -> bool:
        """Create a sample CSV file in S3 for testing"""
        if not self.s3_client:
            return False
        
        try:
            sample_content = """id,date,description,category,priority
1,2026-04-01,Customer complaints about product delivery,complaint,high
2,2026-04-02,Feature request for a new UI design,request,medium
3,2026-04-03,Urgent issue with payment processing,issue,critical
4,2026-04-04,Feedback on the latest update,feedback,low
5,2026-04-05,Customer inquiries regarding subscription,inquiry,medium
6,2026-04-06,Feature request for additional reporting capabilities,request,medium
7,2026-04-07,Issue with password reset functionality,issue,high
8,2026-04-08,Complaints about customer support response time,complaint,high
9,2026-04-09,Feedback on new features,feedback,low
10,2026-04-10,Request for integration with third-party tools,request,medium
11,2026-04-11,Urgent issue with server downtime,issue,critical
12,2026-04-12,Inquiry about billing issues,inquiry,medium"""
            
            file_key = f"{self.prefix}{filename}"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=sample_content.encode('utf-8'),
                ContentType='text/csv'
            )
            
            logger.info(f"Sample file created: {file_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating sample file: {str(e)}")
            return False


s3_polling_service: Optional[S3PollingService] = None

def initialize_s3_polling(bucket_name: str, prefix: str = "incoming/", region: str = "us-east-1") -> S3PollingService:
    global s3_polling_service
    s3_polling_service = S3PollingService(bucket_name, prefix, region)
    return s3_polling_service

def get_s3_polling_service() -> Optional[S3PollingService]:
    return s3_polling_service
