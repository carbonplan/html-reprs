import re

import upath


def s3_to_https(*, s3_url: str) -> str:
    # Split the URL into its components
    s3_parts = s3_url.split('/')

    # Get the bucket name from the first part of the URL
    bucket_name = s3_parts[2]

    # Join the remaining parts of the URL to form the path to the file
    path = '/'.join(s3_parts[3:])

    # Return the HTTPS URL in the desired format
    return f'https://{bucket_name}.s3.amazonaws.com/{path}'


def gs_to_https(*, gs_url: str) -> str:
    return gs_url.replace('gs://', 'https://storage.googleapis.com/')


def parse_s3_url(url: str) -> tuple[str | None, str | None]:
    bucket = None
    key = None

    # https://bucket-name.s3.region-code.amazonaws.com/key-name

    if match := re.search('^https?://([^.]+).s3.([^.]+).amazonaws.com(.*?)$', url):
        bucket, key = match[1], match[3]

    # https://AccessPointName-AccountId.s3-accesspoint.region.amazonaws.com.
    if match := re.search(
        '^https?://([^.]+)-([^.]+).s3-accesspoint.([^.]+).amazonaws.com(.*?)$', url
    ):
        bucket, key = match[1], match[4]

    # S3://bucket-name/key-name
    if match := re.search('^s3://([^.]+)(.*?)$', url):
        bucket, key = match[1], match[2]

    # https://bucket-name.s3.amazonaws.com/key-name
    if match := re.search('^https?://([^.]+).s3.amazonaws.com(.*?)$', url):
        bucket, key = match[1], match[2]

    return bucket, key


def parse_gs_url(url: str) -> tuple[str | None, str | None]:
    bucket = None
    key = None

    # https://storage.googleapis.com/carbonplan-share/maps-demo/2d/prec-regrid
    path = url.split('storage.googleapis.com/')[1]
    bucket, key = path.split('/', 1)
    return bucket, key


def parse_az_url(url: str) -> tuple[str | None, str | None]:
    bucket = None
    key = None

    if match := re.search('^https?://([^.]+).blob.core.windows.net(.*?)$', url):
        bucket, key = match[1], match[2]

    return bucket, key


def sanitize_url(url: str) -> str:
    """Sanitize a URL by removing any trailing slashes and parsing it with universal_pathlib"""

    # Remove trailing slashes
    url = url.rstrip('/')
    url_path = upath.UPath(url)
    parsed_url = url_path._url

    if parsed_url.scheme == 'gs':
        url = gs_to_https(gs_url=url)

    elif parsed_url.scheme == 's3':
        url = s3_to_https(s3_url=url)

    return url
