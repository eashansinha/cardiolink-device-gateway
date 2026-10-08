import json
import os

import boto3
from botocore.exceptions import ClientError

BUCKET = os.environ.get("FIRMWARE_BUCKET", "cardiolink-firmware-images")


def _s3():
    return boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT_URL"))


def get_manifest(device_model: str):
    try:
        obj = _s3().get_object(Bucket=BUCKET, Key=f"{device_model}/manifest.json")
    except ClientError:
        return None
    return json.loads(obj["Body"].read())


def get_image(key: str) -> bytes:
    return _s3().get_object(Bucket=BUCKET, Key=key)["Body"].read()
