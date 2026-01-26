import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
import logging

logger = logging.getLogger(__name__)


class S3Service:
    """Service for AWS S3 operations"""
    
    def __init__(self):
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'forum-uploads')
        
        # Configure boto3 to use AWS Signature Version 4
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.region,
            config=Config(
                signature_version='s3v4',
                s3={
                    'addressing_style': 'virtual'
                }
            )
        )
        
        # Try to get actual bucket region (in case it differs from config)
        # This is CRITICAL because presigned URLs must use the correct region
        print(f'[S3Service] Initializing with bucket: {self.bucket_name}, config region: {self.region}')
        logger.info(f'Initializing S3 service with bucket: {self.bucket_name}, config region: {self.region}')
        
        try:
            # Use a client without region specified to get bucket location
            # This works because get_bucket_location doesn't require region
            temp_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            bucket_location = temp_client.get_bucket_location(Bucket=self.bucket_name)
            
            # get_bucket_location returns None for us-east-1, actual region name for others
            actual_region = bucket_location.get('LocationConstraint')
            
            if actual_region is None or actual_region == '':
                # None or empty means us-east-1 (default region)
                actual_region = 'us-east-1'
            elif actual_region == 'EU':
                # EU means eu-west-1
                actual_region = 'eu-west-1'
            
            print(f'[S3Service] Detected bucket region: {actual_region}, config region: {self.region}')
            logger.info(f'Detected bucket region: {actual_region}, config region: {self.region}')
            
            # Update region if different from config
            if actual_region != self.region:
                print(f'[S3Service] ⚠️  Region mismatch! Updating from {self.region} to {actual_region}')
                logger.warning(f'⚠️  Bucket region ({actual_region}) differs from config ({self.region})!')
                logger.warning(f'Updating to use bucket region: {actual_region}')
                self.region = actual_region
                # Recreate client with correct region
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.region,
                    config=Config(
                        signature_version='s3v4',
                        s3={
                            'addressing_style': 'virtual'
                        }
                    )
                )
                print(f'[S3Service] ✅ Client recreated with region: {self.region}')
                logger.info(f'✅ S3 client recreated with correct region: {self.region}')
            else:
                print(f'[S3Service] ✅ Region matches: {self.region}')
                logger.info(f'✅ Bucket region matches config: {self.region}')
        except Exception as e:
            print(f'[S3Service] ❌ Error detecting region: {str(e)}')
            logger.error(f'❌ Could not determine bucket region: {str(e)}')
            logger.warning(f'Using config region: {self.region}')
            logger.warning('⚠️  Presigned URLs may fail if region is incorrect!')
            logger.warning('Please verify AWS_REGION in .env file matches the actual bucket region.')
        
        # Track region for presigned URL generation
        self._last_region = self.region
    
    def upload_file(self, file, key: str) -> dict:
        """Upload a file to S3"""
        try:
            # Determine content type
            content_type = file.content_type or 'application/octet-stream'
            
            # Try to upload with public-read ACL first (like the reference service)
            # If ACL is disabled, fall back to private upload with presigned URL
            try:
                self.s3_client.upload_fileobj(
                    file,
                    self.bucket_name,
                    key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'ACL': 'public-read'
                    }
                )
                # If ACL worked, use direct public URL
                # Use virtual-hosted-style URL (works with addressing_style: 'virtual')
                url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
                logger.info(f'File uploaded with public-read ACL: {key}, URL: {url}')
            except ClientError as acl_error:
                # ACL might be disabled, try without ACL
                error_code = acl_error.response.get('Error', {}).get('Code', '')
                if error_code in ['InvalidArgument', 'AccessControlListNotSupported']:
                    logger.warning(f'ACL not supported (code: {error_code}), uploading without ACL: {key}')
                    file.seek(0)  # Reset file pointer
                    self.s3_client.upload_fileobj(
                        file,
                        self.bucket_name,
                        key,
                        ExtraArgs={
                            'ContentType': content_type
                        }
                    )
                    # Generate presigned URL (more reliable than direct URL for private buckets)
                    # Use presigned URL as primary method when ACL is disabled
                    presigned_url = self.get_presigned_url(key, expiration=31536000)  # 1 year
                    if presigned_url:
                        url = presigned_url
                        logger.info(f'File uploaded without ACL, using presigned URL: {url[:100]}...')
                    else:
                        # Fallback to direct URL (may not work if bucket is private)
                        url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
                        logger.warning(f'Presigned URL generation failed, using direct URL (may not work): {url}')
                else:
                    # Other error, re-raise
                    logger.error(f'Unexpected ACL error: {error_code} - {str(acl_error)}')
                    raise
            
            logger.info(f'File uploaded: {key}, URL: {url}')
            
            return {
                'key': key,
                'url': url
            }
            
        except ClientError as e:
            logger.error(f'S3 upload error: {str(e)}')
            return None
    
    def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Get a presigned URL for downloading a file using AWS Signature Version 4"""
        try:
            # Log current region before generating URL
            logger.info(f'Generating presigned URL for {key} using region: {self.region}, bucket: {self.bucket_name}')
            
            # Ensure we use a client with the correct region
            # Always recreate client to ensure correct region is used
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.region,  # Use the detected/updated region
                config=Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'virtual'
                    }
                )
            )
            
            # Generate presigned URL with correct region
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            
            # Log the generated URL (first 100 chars to avoid logging sensitive data)
            logger.info(f'Presigned URL generated successfully for {key} in region {self.region}')
            logger.debug(f'URL preview: {url[:100]}...')
            
            return url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f'Error generating presigned URL for {key}: {error_code} - {error_msg}')
            logger.error(f'Current region: {self.region}, bucket: {self.bucket_name}')
            return None
        except Exception as e:
            logger.error(f'Unexpected error generating presigned URL for {key}: {str(e)}')
            logger.error(f'Current region: {self.region}, bucket: {self.bucket_name}')
            return None
    
    def get_presigned_upload_url(self, key: str, expiration: int = 3600) -> dict:
        """Get a presigned URL for uploading a file directly to S3"""
        try:
            response = self.s3_client.generate_presigned_post(
                self.bucket_name,
                key,
                ExpiresIn=expiration
            )
            return response
            
        except ClientError as e:
            logger.error(f'Error generating presigned upload URL: {str(e)}')
            return None
    
    def delete_file(self, key: str) -> bool:
        """Delete a file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f'File deleted: {key}')
            return True
            
        except ClientError as e:
            logger.error(f'S3 delete error: {str(e)}')
            return False
    
    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except ClientError:
            return False
