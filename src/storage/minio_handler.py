import requests
import json
import os
import logging
from dotenv import load_dotenv
import boto3
import hashlib
import io
from typing import Optional, Tuple
import pandas as pd
load_dotenv()

# -------------------------
# MinIO / S3 client setup
# -------------------------

s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"),
    aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY"),
)

BRONZE_BUCKET = "morocco-water-bronze"
QUARANTINE_BUCKET = "morocco-water-quarantine"


def init_bucket():
    for bucket in [BRONZE_BUCKET, QUARANTINE_BUCKET]:
        try:
            s3_client.head_bucket(Bucket=bucket)
        except Exception:
            s3_client.create_bucket(Bucket=bucket)

# -------------------------
# Checksum & validation
# -------------------------

def compute_sha256(file_bytes: bytes) -> str:
    """Compute SHA256 checksum of bytes."""
    return hashlib.sha256(file_bytes).hexdigest()


def is_file_empty(file_bytes: bytes) -> bool:
    return len(file_bytes) == 0


def validate_excel_schema(file_bytes: bytes) -> bool:
    """
    Validate Excel file structure/schema.

    Here we just ensure:
      - file is not empty
      - it can be opened as an Excel workbook
      - it has at least one sheet with at least one row

    Replace/augment this with your real schema rules if needed.
    """
    if is_file_empty(file_bytes):
        return False

    try:
        

        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        if len(xls.sheet_names) == 0:
            return False

        # Check first sheet has at least one row
        first_sheet = xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=first_sheet, nrows=1)
        if df.empty:
            return False

        # TODO more schema checks here


        return True

    except Exception:
        # Corrupt or unreadable Excel file
        return False


def route_to_quarantine(file_bytes: bytes, object_key: str, reason: str) -> None:
    """
    Upload a bad file to the quarantine prefix with metadata about why.
    """
    quarantine_key = f"quarantine/{object_key}"
    file_stream = io.BytesIO(file_bytes)

    s3_client.upload_fileobj(
        file_stream,
        QUARANTINE_BUCKET,
        quarantine_key,
        Metadata={
            "sha256": compute_sha256(file_bytes),
            "quarantine_reason": reason,
        },
    )
    logging.warning(
        f"File quarantined: {quarantine_key} (reason={reason})"
    )


def ingest_to_bronze_or_quarantine(
    file_bytes: bytes,
    base_key: str,
) -> Tuple[bool, str, str]:
    """
    Validate and ingest a file.

    Returns:
        (ok, object_key, reason)
        - ok: True if sent to Bronze, False if quarantined
        - object_key: final key in Bronze or Quarantine
        - reason: None if ok, else reason for quarantine
    """
    init_bucket()  # ensure buckets exist


    if is_file_empty(file_bytes):
        reason = "empty_file"
        route_to_quarantine(file_bytes, base_key, reason)
        return False, f"quarantine/{base_key}", reason


    checksum = compute_sha256(file_bytes)


    
    if not validate_excel_schema(file_bytes):
        reason = "schema_invalid_or_corrupt"
        route_to_quarantine(file_bytes, base_key, reason)
        return False, f"quarantine/{base_key}", reason


    file_stream = io.BytesIO(file_bytes)
    s3_client.upload_fileobj(
        file_stream,
        BRONZE_BUCKET,
        base_key,
        ExtraArgs={"Metadata": {"sha256": checksum}},
    )
    logging.info(f"Successfully uploaded {base_key} to MinIO Bronze (sha256={checksum}).")
    return True, base_key, None


# -------------------------
# Download & ingest logic
# -------------------------

def download_resources(datasets):
    """Downloads resources from the extracted datasets and ingests them."""
    for dataset in datasets:
        logging.info(f"Dataset Title: {dataset.get('title')}")
        resources = dataset.get("resources", [])

        if not resources:
            logging.warning(f"No resources found for dataset: {dataset.get('title')}")
            continue

        for resource in resources:
            file_name = resource.get("name")
            file_url = resource.get("url")
            file_format = resource.get("format", "").lower()

            logging.info(f" - File Name: {file_name}")
            logging.info(f" - Format: {file_format}")
            logging.info(f" - Download URL: {file_url}\n")

            try:
                response = requests.get(file_url, stream=True, timeout=30)
                if response.status_code != 200:
                    logging.error(
                        f"Failed to download resource {file_name}: "
                        f"status_code={response.status_code}"
                    )
                    continue

                file_bytes = response.content

                # Decide base key depending on format / dataset
                if file_format in ("xlsx", "xls"):
                    ext = ".xlsx"
                else:
                    ext = ""  # TODO handle other formats separately

                base_key = f"raw/tensift_reservoirs/{file_name}{ext}"

                ok, object_key, reason = ingest_to_bronze_or_quarantine(
                    file_bytes,
                    base_key,
                )

                if not ok:
                    logging.warning(
                        f"File {file_name} was quarantined (reason={reason})."
                    )

            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to download resource {file_name}: {e}")


def upload_json_to_minio(data_dict: dict, object_key: str) -> bool:
    """
    Serializes a Python dictionary to JSON and uploads it to MinIO.
    """
    try:
        # Convert dict to JSON string, then to bytes
        json_bytes = json.dumps(data_dict).encode('utf-8')
        
        # (reusing data quality logic)
        checksum = hashlib.sha256(json_bytes).hexdigest()
        
         # Wrap in a file-like stream
        file_stream = io.BytesIO(json_bytes)
        
        s3_client.upload_fileobj(
            file_stream, 
            "morocco-water-bronze", 
            object_key,
            ExtraArgs={"Metadata": {"sha256": checksum}}
        )
        
        logging.info(f"Successfully uploaded JSON to {object_key}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to upload JSON to MinIO: {e}")
        return False      

def get_json_from_minio(object_key: str) -> Optional[dict]:
    """
    Retrieves a JSON object from MinIO and returns it as a Python dictionary.
    """
    try:
        response = s3_client.get_object(Bucket="morocco-water-bronze", Key=object_key)
        file_content = response['Body'].read().decode('utf-8')
        return json.loads(file_content)
    except Exception as e:
        logging.error(f"Failed to retrieve JSON from MinIO: {e}")
        return {}


def upload_parquet_to_minio(df: pd.DataFrame,bucket_name: str, object_key: str) -> bool:
    """
    Serializes a Pandas DataFrame to Parquet and uploads it to MinIO.
    """
    try:
        parquet_buffer = io.BytesIO()

        df.to_parquet(parquet_buffer, engine='pyarrow', index=False)

        parquet_buffer.seek(0)

        s3_client.upload_fileobj(
            parquet_buffer, 
            bucket_name, 
            object_key,
            ExtraArgs={"ContentType": "application/octet-stream"}
        )
        
        logging.info(f"Successfully uploaded Parquet to {object_key}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to upload Parquet to MinIO: {e}")
        return False


def get_excel_from_minio(bucket_name: str, object_key: str) -> pd.DataFrame:
    """
    Downloads an Excel file from MinIO and loads it directly into a Pandas DataFrame.
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_bytes = response['Body'].read()
        
        df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
        return df
    except Exception as e:
        logging.error(f"Failed to fetch Excel from {object_key}: {e}")
        return pd.DataFrame()

def list_objects_in_prefix(bucket_name: str, prefix: str) -> list:
    """
    Lists all object keys in a specific MinIO bucket under a given folder prefix.
    """
    try:
        # Ensure the prefix ends with a slash so we only search inside that folder
        if not prefix.endswith('/'):
            prefix += '/'

        # Query MinIO for all objects in this path
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        
        keys = []
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                # Skip the directory marker itself if MinIO returns it
                if key != prefix:
                    keys.append(key)
                    
        return keys
        
    except Exception as e:
        logging.error(f"Failed to list objects in {bucket_name}/{prefix}: {e}")
        return []