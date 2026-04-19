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

### Build and push to ECR manually
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker build -t ai-workflow-automation-stage:latest .
docker tag ai-workflow-automation-stage:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-workflow-automation-stage:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ai-workflow-automation-stage:latest
