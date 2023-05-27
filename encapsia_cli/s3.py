import typing as T
from itertools import repeat

import boto3
import botocore


class S3Error(Exception):
    pass


def list_bucket(bucket: str, prefix: str = "") -> T.Iterable[dict]:
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
    try:
        for page in page_iterator:
            yield from page.get("Contents", [])
    except botocore.exceptions.ClientError as e:
        raise S3Error(f"Unable to search bucket: {bucket}: {e}") from e


def list_buckets(bucket_paths: T.Iterable[str]) -> T.Iterable[T.Tuple[str, dict]]:
    for bucket_path in bucket_paths:
        if "/" in bucket_path:
            bucket, prefix = bucket_path.split("/", 1)
        else:
            bucket, prefix = bucket_path, ""
        yield from zip(repeat(bucket), list_bucket(bucket, prefix))


def download_file(bucket, name, target):
    s3 = boto3.client("s3")
    try:
        s3.download_file(bucket, name, target)
    except botocore.exceptions.ClientError as e:
        raise S3Error(f"Unable to download: {bucket}/{name}") from e
