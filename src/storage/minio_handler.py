import requests
import json
import os 
import logging
from dotenv import load_dotenv
import boto3

s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"),
    aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY"),
    aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY"),
)
BUCKET_NAME = "morocco-water-bronze"

load_dotenv()

try:
  s3_client.head_bucket(Bucket=BUCKET_NAME)
except Exception:
  s3_client.create_bucket(Bucket=BUCKET_NAME)

def download_resources(datasets):
    """
    Downloads resources from the extracted datasets.

    Args:
        datasets (list): A list of dictionaries representing the extracted datasets.
    """
    for dataset in datasets:
        logging.info(f"Dataset Title: {dataset.get('title')}")
        resources = dataset.get("resources", [])
        if not resources:
            logging.warning(f"No resources found for dataset: {dataset.get('title')}")
            continue    
        for resource in resources:
            logging.info(f" - File Name: {resource.get('name')}")
            logging.info(f" - Format: {resource.get('format')}")
            logging.info(f" - Download URL: {resource.get('url')}\n")
            response = requests.get(resource.get('url'), stream=True)
            if response.status_code == 200:
                response.raw.decode_content = True
                # stream directly into MinIO Bronze layer
                object_key = f"raw/tensift_reservoirs/{resource.get('name')}.xlsx"
                s3_client.upload_fileobj(response.raw, BUCKET_NAME, object_key)
                logging.info(f"Successfully streamed {object_key} to MinIO Bronze layer.")   