import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from app.utils.logger import logger
from typing import Optional
import uuid
from pathlib import Path


DEFAULT_PRESIGNED_URL_EXPIRATION = 3600 


class S3Service:
    """
    S3 service for handling file uploads and operations
    """
    
    def __init__(self):
        """Initialize S3 client with credentials from environment variables"""
        self.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region_name = os.getenv('AWS_REGION', 'us-west-2')
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME', 'simmpli-staging')
        endpoint_url = os.getenv('AWS_S3_ENDPOINT_URL')
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            logger.error("AWS credentials not found in environment variables")
            raise ValueError("AWS credentials not configured")
        
        try:
            if endpoint_url: 
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name,
                    endpoint_url=endpoint_url
                )
            else:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name
                )
            logger.info(f"S3 client initialized successfully for region: {self.region_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def upload_file(self, file_path: str, object_key: str, content_type: Optional[str] = None) -> str:
        """
        Upload a file to S3 bucket
        
        Args:
            file_path (str): Path to the local file to upload
            object_key (str): S3 object key (path in bucket)
            content_type (str, optional): MIME type of the file
            
        Returns:
            str: Public URL of the uploaded file
            
        Raises:
            Exception: If upload fails
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            # Upload file to S3
            self.s3_client.upload_file(
                file_path, 
                self.bucket_name, 
                object_key,
                ExtraArgs=extra_args
            )
            
            # Generate public URL
            url = f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{object_key}"
            
            logger.info(f"Successfully uploaded {file_path} to S3: {url}")
            return url
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise Exception(f"File not found: {file_path}")
        except NoCredentialsError:
            logger.error("AWS credentials not available")
            raise Exception("AWS credentials not configured")
        except ClientError as e:
            logger.error(f"AWS S3 upload failed: {str(e)}")
            raise Exception(f"S3 upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {str(e)}")
            raise Exception(f"Upload failed: {str(e)}")
    
    def upload_image(self, file_path: str, folder: str = "uploads") -> str:
        """
        Upload an image file to S3 with automatic naming and path generation
        
        Args:
            file_path (str): Path to the local image file
            folder (str): S3 folder/prefix (default: "uploads")
            
        Returns:
            str: Public URL of the uploaded image
        """
        try:
            # Generate unique filename
            file_extension = Path(file_path).suffix
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            object_key = f"{folder}/{unique_filename}"
            
            # Determine content type based on file extension
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp'
            }
            content_type = content_type_map.get(file_extension.lower(), 'image/jpeg')
            
            return self.upload_file(file_path, object_key, content_type)
            
        except Exception as e:
            logger.error(f"Error uploading image to S3: {str(e)}")
            raise
    
    def delete_file(self, s3_path_or_url: str) -> bool:
        """
        Delete a file from S3 bucket.
        This helper now accepts **either** a raw S3 object key (e.g. ``folder/filename.jpg``)
        or a complete S3 URL (e.g. ``https://my-bucket.s3.us-west-2.amazonaws.com/folder/filename.jpg``
        or ``s3://my-bucket/folder/filename.jpg``).
        
        Args:
            s3_path_or_url (str): S3 object key **or** full S3 URL to delete.
        
        Returns:
            bool: True if deletion request succeeded, False otherwise.
        """
        try:
            # Determine whether input is a URL or a direct object key
            if s3_path_or_url.startswith("http://") or s3_path_or_url.startswith("https://"):
                # Parse HTTP(S) style S3 URL
                from urllib.parse import urlparse
                parsed_url = urlparse(s3_path_or_url)
                # The path contains the object key
                object_key = parsed_url.path.lstrip("/")
                # Attempt to derive bucket from host if it is in <bucket>.s3.<region>.amazonaws.com format
                host_parts = parsed_url.hostname.split(".") if parsed_url.hostname else []
                bucket_name = host_parts[0] if host_parts else self.bucket_name
            elif s3_path_or_url.startswith("s3://"):
                # Parse s3://bucket/key style URL
                without_scheme = s3_path_or_url[5:]
                bucket_name, object_key = without_scheme.split("/", 1)
                bucket_name = bucket_name or self.bucket_name
            else:
                # Assume a plain object key was provided
                bucket_name = self.bucket_name
                object_key = s3_path_or_url

            # Default to instance bucket if derived bucket is None
            bucket_name = bucket_name or self.bucket_name

            self.s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            logger.info(f"Successfully deleted S3 object: {bucket_name}/{object_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete S3 object {s3_path_or_url}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting S3 object {s3_path_or_url}: {str(e)}")
            return False
    
    def generate_presigned_url(self, object_key: str, expiration: int = DEFAULT_PRESIGNED_URL_EXPIRATION) -> Optional[str]:
        """
        Generate a presigned URL for S3 object
        
        Args:
            object_key (str): S3 object key
            expiration (int): URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {object_key}: {str(e)}")
            return None


# Create a singleton instance
s3_service = S3Service() 