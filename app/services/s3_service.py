# s3_service.py
# Service for handling S3 file uploads

import boto3
from botocore.exceptions import ClientError
from flask import current_app
from werkzeug.datastructures import FileStorage

class S3Service:
    def __init__(self):
        self.s3_client = None
    
    def _get_client(self):
        if self.s3_client is None:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
                    aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
                    region_name=current_app.config['AWS_REGION']
                )
            except Exception as e:
                print(f"Error initializing S3 client: {e}")
                raise
        return self.s3_client
    
    def upload_file(self, file: FileStorage, filename: str) -> str:
        """ 
        Returns:
            str: Public URL of the uploaded file
            Format: https://{bucket}.s3.{region}.amazonaws.com/{filename}
        """
        bucket_name = current_app.config['S3_BUCKET_NAME']
        
        try:
            file.seek(0)
            
            s3_client = self._get_client()
            
            s3_client.upload_fileobj(
                file,
                bucket_name,
                filename,
                ExtraArgs={
                    'ContentType': file.content_type or 'image/jpeg',
                    'ACL': 'public-read'
                }
            )
            
            region = current_app.config['AWS_REGION']
            url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{filename}"
            
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise Exception(f"S3 upload failed: {error_code} - {error_message}")
        except Exception as e:
            raise Exception(f"Unexpected error during upload: {str(e)}")
