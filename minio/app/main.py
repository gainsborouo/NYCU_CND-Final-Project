from fastapi import FastAPI, HTTPException
from minio import Minio
from minio.error import S3Error
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import json
from pathlib import Path
from datetime import timedelta
import os

app = FastAPI()

# MinIO configuration from environment variables
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin1234")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
BUCKET_NAME = "documents"

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Ensure bucket exists
def ensure_bucket():
    try:
        if not minio_client.bucket_exists(BUCKET_NAME):
            minio_client.make_bucket(BUCKET_NAME)
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {e}")

ensure_bucket()

class UploadUrlRequest(BaseModel):
    filename: str

@app.post("/generate-upload-url/{uid}")
async def generate_upload_url(uid: str, request: UploadUrlRequest):
    """
    Generate a presigned URL for uploading a file to MinIO under uid-specific path.
    """
    try:
        # Determine file type based on extension
        file_ext = Path(request.filename).suffix.lower()
        if file_ext in [".md", ".markdown"]:
            folder = f"{uid}/markdown"
        elif file_ext in [".png", ".jpg", ".jpeg"]:
            folder = f"{uid}/images"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        # Construct object name
        object_name = f"{folder}/{request.filename}"

        # Generate presigned URL for upload (PUT request)
        presigned_url = minio_client.presigned_put_object(
            BUCKET_NAME,
            object_name,
            expires=timedelta(seconds=3600)  # 1-hour expiry
        )

        return JSONResponse(
            status_code=200,
            content={"message": "Upload URL generated successfully", "url": presigned_url}
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}")

@app.get("/files/{uid}/{file_path:path}")
async def redirect_file(uid: str, file_path: str):
    """
    Redirect a file from MinIO under uid-specific path.
    """
    # get file type based on file extension
    file_ext = Path(file_path).suffix.lower()
    if file_ext in [".md", ".markdown"]:
        folder = f"markdown"
    elif file_ext in [".png", ".jpg", ".jpeg"]:
        folder = f"images"
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Construct full object name
    object_name = f"{uid}/{folder}/{file_path}"

    # Verify object exists
    try:
        minio_client.stat_object(BUCKET_NAME, object_name)
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found")
        raise

    temp_read = await generate_read_url(uid, f"{folder}/{file_path}")
    if temp_read.status_code != 200:
        raise HTTPException(status_code=temp_read.status_code)

    return RedirectResponse(
        json.loads(temp_read.body.decode()).get("url")
    )

@app.get("/generate-read-url/{uid}/{file_path:path}")
async def generate_read_url(uid: str, file_path: str):
    """
    Generate a presigned URL for reading a file from MinIO under uid-specific path.
    """
    try:
        # Construct full object name
        object_name = f"{uid}/{file_path}"

        # Verify object exists
        try:
            minio_client.stat_object(BUCKET_NAME, object_name)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise HTTPException(status_code=404, detail="File not found")
            raise

        # Generate presigned URL for read (GET request)
        presigned_url = minio_client.presigned_get_object(
            BUCKET_NAME,
            object_name,
            expires=timedelta(seconds=3600)  # 1-hour expiry
        )

        return JSONResponse(
            status_code=200,
            content={"message": "Read URL generated successfully", "url": presigned_url}
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {e}")
