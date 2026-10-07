import os

import boto3

s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    aws_access_key_id="{{FAKE_AWS_KEY_ID}}",
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)


def upload_avatar(user_id: int, data: bytes) -> str:
    key = f"avatars/{user_id}.png"
    s3.put_object(Bucket="acme-uploads", Key=key, Body=data, ContentType="image/png")
    return key
