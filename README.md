# NYCU_CN-Final-Project

## minio-api usage

### Generate an upload URL for a file
```
curl -X POST http://minio-api:8000/generate-upload-url/{UID} \
  -H 'Content-Type: application/json' \
  -d '{
    "filename": "example.md"
}'
```
#### Response
```json
{
    "message":"Upload URL generated successfully",
    "url":"http://minio:9000/documents/{UID}/markdown/example.md?.............."
}
```

#### Upload the file to MinIO
```
curl -X PUT -T example.md "http://minio:9000/documents/{UID}/markdown/example.md?.............."
```

### Generate a read URL for a file
```
curl http://minio-api:8000/generate-read-url/{UID}/markdown/example.md
```

#### Response
```json
{
    "message":"Read URL generated successfully",
    "url":"http://minio:9000/documents/{UID}/markdown/example.md?.............."
}
```

curl that presigned URL to read the file
