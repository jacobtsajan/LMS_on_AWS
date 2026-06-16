"""
Shared AWS SDK configuration for all LMS services.
Points all clients at the Floci emulator endpoint.
"""
import boto3
import os

AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'test')

# Resource identifiers
TABLE_NAME = 'lms-books'
SNS_TOPIC_ARN = f'arn:aws:sns:{AWS_REGION}:000000000000:book-events-topic'
SQS_QUEUE_URL = f'{AWS_ENDPOINT_URL}/000000000000/inventory-update-queue'

_boto_kwargs = dict(
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=AWS_ENDPOINT_URL,
)


def get_dynamodb_resource():
    """Return a boto3 DynamoDB resource (high-level Table API)."""
    return boto3.resource('dynamodb', **_boto_kwargs)


def get_sns_client():
    """Return a boto3 SNS client."""
    return boto3.client('sns', **_boto_kwargs)


def get_sqs_client():
    """Return a boto3 SQS client."""
    return boto3.client('sqs', **_boto_kwargs)
