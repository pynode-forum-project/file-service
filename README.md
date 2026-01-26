# File Service

A microservice for managing file uploads, downloads, and deletions using AWS S3.

## Features

- File upload/download/delete operations
- Presigned URLs for secure file access
- Direct client-to-S3 upload support
- File organization by type (profile, post, attachment, general)
- File validation (type and size limits)

## Tech Stack

- Flask 3.0.0
- AWS S3 (boto3 1.34.14)
- JWT authentication via headers

## Environment Variables

```env
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
JWT_SECRET=your-super-secret-jwt-key
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1
S3_BUCKET_NAME=forum-uploads
```

## Installation

```bash
pip install -r requirements.txt
python run.py
```

Service runs on `http://localhost:5005`

## File Organization

Files are stored in S3 with structure: `{file_type}/{user_id}/{uuid}.{extension}`

- File types: `profile`, `post`, `attachment`, `general`
- Max file size: 16 MB
- Allowed extensions: `png`, `jpg`, `jpeg`, `gif`, `pdf`, `doc`, `docx`, `txt`

## API Endpoints

### Upload File
**POST** `/files/upload`
- Headers: `Authorization: Bearer <token>`, `X-User-Id: <id>`
- Body: `multipart/form-data` with `file` and optional `type`
- Returns: `{ "key": "...", "url": "..." }`

### Get File URL
**GET** `/files/{key}`
- Headers: `Authorization: Bearer <token>`, `X-User-Id: <id>`
- Returns: Presigned URL for file download

### Delete File
**DELETE** `/files/{key}`
- Headers: `Authorization: Bearer <token>`, `X-User-Id: <id>`, `X-User-Type: <type>`
- Only owner or admin can delete

### Get Presigned Upload URL
**POST** `/files/presigned-upload`
- Headers: `Authorization: Bearer <token>`, `X-User-Id: <id>`
- Body: `{ "filename": "...", "type": "..." }`
- Returns: Presigned URL and form fields for direct S3 upload

### Health Check
**GET** `/health`

## Authentication

All endpoints require:
- `X-User-Id`: User ID from JWT token
- `X-User-Type`: User role (for admin access)

## AWS S3 Setup

1. Create S3 bucket
2. Configure IAM user with permissions:
   - `s3:PutObject`
   - `s3:GetObject`
   - `s3:DeleteObject`
   - `s3:GetBucketLocation`
3. Set bucket CORS for direct client uploads (optional)

## Error Codes

- **400**: Bad Request (invalid file type, missing file)
- **401**: Unauthorized
- **403**: Forbidden (not owner/admin)
- **404**: File not found
- **413**: File too large (>16 MB)
- **500**: Internal Server Error
