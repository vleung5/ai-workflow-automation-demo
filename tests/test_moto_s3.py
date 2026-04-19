"""Sample tests demonstrating AWS S3 mocking with Moto.

These tests use Moto to intercept Boto3 calls so no real AWS credentials
or infrastructure are required during local development and CI.
"""

import boto3
import pytest
from moto import mock_aws


BUCKET_NAME = "test-bucket"
OBJECT_KEY = "test-object.txt"
OBJECT_BODY = b"Hello from Moto!"


@pytest.fixture
def s3_client():
    """Provide a Boto3 S3 client backed by Moto's in-memory mock."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET_NAME)
        yield client


def test_put_and_get_object(s3_client):
    """Uploading an object and retrieving it returns the original content."""
    s3_client.put_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY, Body=OBJECT_BODY)

    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)
    body = response["Body"].read()

    assert body == OBJECT_BODY


def test_list_objects_after_put(s3_client):
    """After uploading an object the bucket listing includes that key."""
    s3_client.put_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY, Body=OBJECT_BODY)

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    keys = [obj["Key"] for obj in response.get("Contents", [])]

    assert OBJECT_KEY in keys


def test_delete_object(s3_client):
    """Deleting an object removes it from the bucket."""
    s3_client.put_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY, Body=OBJECT_BODY)
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY)

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    keys = [obj["Key"] for obj in response.get("Contents", [])]

    assert OBJECT_KEY not in keys
