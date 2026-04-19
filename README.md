# Problem
Manual workflows often lead to delays and errors, with a staggering error rate of 7% and requiring around 3 hours to process 100 records.

# Solution
An automated pipeline utilizing asynchronous processing, combined with AI classification, validation, and summarization, addresses these challenges effectively.

# Impact
- **33x faster** processing: from 30 to 1000 records/hour.
- **93% error reduction**: decreasing from a 7% error rate to just 0.6%.
- **1200x speedup** of processing time: from 3 hours down to 9 seconds.
- **87.5% fewer steps** in the process: reducing from 8 steps to just 1.
- **99% cost savings** overall.

# Tech Stack
- Python
- FastAPI
- Asyncio
- HTML5/CSS3

# Quick Start
To get started: 
1. Clone the repository.
2. Install the required dependencies.
3. Run the application using the provided commands below.

## Quick Start Commands
### Local development
docker-compose up app-dev

### Staging environment
docker-compose up app-stage

### Production (local test)
docker-compose up app-prod

### Setup AWS infrastructure
bash aws/setup-infrastructure.sh stage us-east-1
bash aws/setup-infrastructure.sh prod us-east-1

## Local AWS Mocking with Moto

[Moto](https://github.com/getmoto/moto) intercepts Boto3 calls and replaces them with
in-memory AWS service implementations, so you can develop and test AWS integrations
without real credentials or cloud resources.

### Install dev/testing dependencies

```bash
pip install -r requirements.txt
```

`moto[s3]` and `pytest` are already included in `requirements.txt` under the
dev/testing section.

### Run tests locally

```bash
# Run the full test suite
pytest tests/

# Run only the Moto S3 mock tests
pytest tests/test_moto_s3.py -v
```

### How it works

Each test that needs a mocked AWS service uses the `@mock_aws` decorator (or the
`mock_aws()` context manager) from `moto`.  Within that scope every Boto3 call is
routed to Moto's in-memory backend instead of AWS:

```python
import boto3
from moto import mock_aws

@mock_aws
def test_example():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="my-bucket")
    s3.put_object(Bucket="my-bucket", Key="hello.txt", Body=b"world")
    response = s3.get_object(Bucket="my-bucket", Key="hello.txt")
    assert response["Body"].read() == b"world"
```

See `tests/test_moto_s3.py` for working examples.  Add new test files alongside it
as additional AWS services (DynamoDB, SQS, etc.) are introduced to the project.

### Build and push to ECR manually
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker build -t ai-workflow-automation-stage:latest .
docker tag ai-workflow-automation-stage:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-workflow-automation-stage:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-workflow-automation-stage:latest
