def get_s3_url_from_id(document_id: int) -> str:
    """
    Placeholder for a function that generates a document URL (e.g., S3 pre-signed URL).
    In a real application, this would interact with your storage service.
    """
    # This is a dummy URL for demonstration purposes
    return f"https://your-s3-bucket.amazonaws.com/documents/{document_id}.pdf"

import httpx
from pydantic import BaseModel
import os
# Assuming your FastAPI app is running locally on port 8000
MINIO_BASE_URL = os.getenv("MINIO_BASE_URL", "http://minio-api:8000")

class UploadUrlRequest(BaseModel):
    filename: str

async def get_upload_s3_url(uid: str, filename: str) -> str:
    """
    Calls the /generate-upload-url/{uid} API to get an S3 upload URL.

    Args:
        uid: The user ID.
        filename: The name of the file to upload.

    Returns:
        The generated S3 upload URL.
    Raises:
        httpx.HTTPStatusError: If the API call returns a non-2xx status code.
    """
    url = f"{MINIO_BASE_URL}/generate-upload-url/{uid}"
    payload = UploadUrlRequest(filename=filename)
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload.model_dump()) # Use model_dump() for Pydantic v2+
        # response.raise_for_status()  # Raise an exception for bad status codes
        resp=response.json()
        return resp.get("url", "")  # Return the URL from the response, defaulting to empty string if not found

async def get_read_s3_url(uid: str, file_path: str) -> str:
    """
    Calls the /generate-read-url/{uid}/{file_path:path} API to get an S3 read URL.

    Args:
        uid: The user ID.
        file_path: The full path of the file in S3.

    Returns:
        The generated S3 read URL.
    Raises:
        httpx.HTTPStatusError: If the API call returns a non-2xx status code.
    """
    # httpx will automatically handle URL encoding for file_path
    url = f"{MINIO_BASE_URL}/generate-read-url/{uid}/{file_path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        # response.raise_for_status()  # Raise an exception for bad status codes
        resp=response.json()
        return resp.get("url", "")  # Return the URL from the response, defaulting to empty string if not found
