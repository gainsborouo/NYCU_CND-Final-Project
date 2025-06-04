# NYCU_CN-Final-Project

## Setup locally
1. Revise `.env` file
2. Use `docker compose up -d` to test the cluster
3. Use browser to visit `http://localhost:8080` to see the web app

## Startup project
Revise `.env` file in several folders, then use the following command to start the cluster.

In production environment, use
```
$ docker compose -f docker-compose.prod.yml up -d
```
to start the cluster with images built from github actions.

## Test
### Backend
```
$ uv run pytest
```

### Frontend
```
$ npx playwright test
```

## Technical Stack
### Frontend
- Vue

### Backend
- FastAPI
- MinIO
- PostgreSQL

## Function
### Backend
- Auth
  - Handle Oauth and group/role management
- Flow
  - Handle document flow
- minio-api
  - Handle file upload/download URL for MinIO
