# File Service

File Service is a Flask-based microservice that handles image file uploads to AWS S3 for the Forum Project. This service is used by other services (post, reply, message) when they need to attach images.

## Tech Stack

- **Framework**: Flask 3.0
- **Storage**: AWS S3
- **AWS SDK**: boto3

## Project Structure

```
file-service/
├── app/
│   ├── __init__.py              # Flask application factory
│   ├── config.py                # Configuration (S3, file settings)
│   ├── routes/
│   │   ├── __init__.py
│   │   └── upload_routes.py    # Upload endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   └── s3_service.py       # S3 upload service
│   └── utils/
│       ├── __init__.py
│       └── file_validator.py   # File validation utilities
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
└── README.md
```

## API Endpoints

### POST /api/files/upload

Upload an image file to S3.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: Form data with `file` field containing the image file

**Response (Success - 200):**
```json
{
  "message": "File uploaded successfully",
  "url": "https://forum-project-files.s3.us-east-1.amazonaws.com/{unique-filename}.jpg"
}
```

**Response (Error - 400):**
```json
{
  "message": "File validation failed",
  "error": "File type not allowed. Allowed types: png, jpg, jpeg, gif, webp"
}
```

**Response (Error - 500):**
```json
{
  "message": "Upload failed",
  "error": "Error details"
}
```

## Configuration

The service uses environment variables loaded from a `.env` file for configuration.

### Environment Variables

Create a `.env` file in the root directory (see `.env.example` for template):

- `AWS_ACCESS_KEY_ID`: AWS access key (required)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (required)
- `AWS_REGION`: AWS region (default: us-east-1)
- `S3_BUCKET_NAME`: S3 bucket name (default: forum-project-files)
- `SECRET_KEY`: Flask secret key (default: file-service-secret-key)

**Note:** The `.env` file is already included in `.gitignore` to prevent committing sensitive credentials.

### Other Settings

- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 10MB) - configured in `config.py`
- `ALLOWED_EXTENSIONS`: Allowed file extensions (default: png, jpg, jpeg, gif, webp) - configured in `config.py`

## File Validation

- Only image files are allowed (png, jpg, jpeg, gif, webp)
- Maximum file size: 10MB
- Files are automatically assigned unique UUID-based filenames to prevent conflicts

## Usage

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
# Copy the example file and fill in your credentials
cp .env.example .env
# Edit .env with your AWS credentials
```

3. Run the service:
```bash
python run.py
```

The service will run on `http://0.0.0.0:5003`

## Example Usage

```bash
curl -X POST http://localhost:5003/api/files/upload \
  -F "file=@/path/to/image.jpg"
```

Response:
```json
{
  "message": "File uploaded successfully",
  "url": "https://forum-project-files.s3.us-east-1.amazonaws.com/123e4567-e89b-12d3-a456-426614174000.jpg"
}
```

## Integration with Other Services

Other services (post, reply, message) can call this service to upload images:

1. Make a POST request to `/api/files/upload` with the image file
2. Receive the S3 URL in the response
3. Store the URL in their database records
