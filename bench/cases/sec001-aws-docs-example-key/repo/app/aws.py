import boto3

from app.settings import settings


def s3_client():
    if settings.use_localstack:
        # LocalStack accepts any credentials; this is the example key id from the AWS docs.
        return boto3.client(
            "s3",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="{{FAKE_AWS_DOCS_EXAMPLE}}",
            aws_secret_access_key="test",
        )
    return boto3.client("s3")
