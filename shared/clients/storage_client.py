import os
import logging
from pathlib import Path
from typing import Union, Optional
from urllib.parse import urljoin, urlparse
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import requests
import uuid
import re

logger = logging.getLogger(__name__)

# Backends that speak the S3 API and therefore share one boto3-backed code
# path: DigitalOcean Spaces, AWS S3, Google Cloud Storage (via its S3
# interoperability endpoint), and Cloudflare R2. Azure Blob Storage uses a
# different API/auth model and is handled by a separate branch below.
S3_LIKE_BACKENDS = {'do_spaces', 's3', 'gcs', 'r2'}

# Per-backend defaults: (bucket env, endpoint env, key env, secret env,
# base-url env, region env, default endpoint template, default region).
# All of these fall back to generic AWS_*-style env vars where a
# provider-specific one isn't set, so e.g. an existing AWS_ACCESS_KEY_ID
# picked up by other tooling also works here without duplication.
_S3_LIKE_ENV_DEFAULTS = {
    'do_spaces': {
        'bucket_env': 'DO_SPACES_BUCKET',
        'endpoint_env': 'DO_SPACES_ENDPOINT',
        'key_env': 'DO_SPACES_KEY',
        'secret_env': 'DO_SPACES_SECRET',
        'base_url_env': 'DO_SPACES_BASE_URL',
        'region_env': 'DO_SPACES_REGION',
        'default_bucket': 'ai-image-gen',
        'endpoint_template': 'https://{region}.digitaloceanspaces.com',
        'default_region': 'nyc3',
    },
    's3': {
        'bucket_env': 'AWS_S3_BUCKET',
        'endpoint_env': 'AWS_S3_ENDPOINT',
        'key_env': 'AWS_ACCESS_KEY_ID',
        'secret_env': 'AWS_SECRET_ACCESS_KEY',
        'base_url_env': 'AWS_S3_BASE_URL',
        'region_env': 'AWS_REGION',
        'default_bucket': None,
        # None endpoint_url tells boto3 to use AWS's real (non-custom) endpoint.
        'endpoint_template': None,
        'default_region': 'us-east-1',
    },
    'gcs': {
        'bucket_env': 'GCS_BUCKET',
        'endpoint_env': 'GCS_ENDPOINT',
        'key_env': 'GCS_HMAC_ACCESS_KEY',
        'secret_env': 'GCS_HMAC_SECRET',
        'base_url_env': 'GCS_BASE_URL',
        'region_env': 'GCS_REGION',
        'default_bucket': None,
        'endpoint_template': 'https://storage.googleapis.com',
        'default_region': 'auto',
    },
    'r2': {
        'bucket_env': 'R2_BUCKET',
        'endpoint_env': 'R2_ENDPOINT',
        'key_env': 'R2_ACCESS_KEY_ID',
        'secret_env': 'R2_SECRET_ACCESS_KEY',
        'base_url_env': 'R2_BASE_URL',
        'region_env': 'R2_REGION',
        'default_bucket': None,
        # R2 endpoints are per-account: https://<account_id>.r2.cloudflarestorage.com
        'endpoint_template': None,
        'default_region': 'auto',
    },
}


class StorageClient:
    """
    Storage client to handle file storage across local disk and any
    S3-compatible object store (DigitalOcean Spaces, AWS S3, Google Cloud
    Storage, Cloudflare R2) or Azure Blob Storage, selected via
    STORAGE_BACKEND. Uses environment variables for configuration.
    """

    def __init__(self):
        """Initialize storage client with configuration from environment"""
        # Get storage backend from environment
        self.storage_backend = os.getenv('STORAGE_BACKEND', 'local')

        # Base paths for different types of storage
        self.base_paths = {
            'character_generation': os.getenv('CHARACTER_GENERATION_PATH', 'character_generation/output'),
            'pose_generation': os.getenv('POSE_GENERATION_PATH', 'pose_generation/output'),
            'model_training': os.getenv('MODEL_TRAINING_PATH', 'model_training/output'),
            'model_generation': os.getenv('MODEL_GENERATION_PATH', 'model_generation/output'),
        }

        # Local storage config
        self.local_base_path = os.getenv('LOCAL_STORAGE_BASE_PATH', './media')

        if self.storage_backend in S3_LIKE_BACKENDS:
            self._init_s3_like_backend()
        elif self.storage_backend == 'azure_blob':
            self._init_azure_backend()
        else:
            logger.info("Using local storage backend")
            self.storage_backend = 'local'

    def _init_s3_like_backend(self):
        """Configure the boto3 S3 client shared by every S3-compatible backend."""
        cfg = _S3_LIKE_ENV_DEFAULTS[self.storage_backend]
        logger.info(f"Initializing {self.storage_backend} storage backend")

        region = os.getenv(cfg['region_env'], cfg['default_region'])
        self.do_spaces_bucket = os.getenv(cfg['bucket_env'], cfg['default_bucket'])
        default_endpoint = (
            cfg['endpoint_template'].format(region=region) if cfg['endpoint_template'] else None
        )
        self.do_spaces_endpoint = os.getenv(cfg['endpoint_env'], default_endpoint)
        self.do_spaces_key = os.getenv(cfg['key_env'])
        self.do_spaces_secret = os.getenv(cfg['secret_env'])
        self.do_spaces_region = region

        if not self.do_spaces_bucket:
            logger.error(f"{cfg['bucket_env']} not set; falling back to local storage")
            self.storage_backend = 'local'
            return

        # Handle multiple possible env vars to decide which public base URL to use.
        # Priority: explicitly supplied CDN endpoint -> origin endpoint -> generic base URL / fallback
        cdn_endpoint = os.getenv('DO_SPACES_CDN_ENDPOINT') if self.storage_backend == 'do_spaces' else None
        origin_endpoint = os.getenv('DO_SPACES_ORIGIN_ENDPOINT') if self.storage_backend == 'do_spaces' else None
        base_url_env = os.getenv(cfg['base_url_env'])

        if cdn_endpoint:
            self.do_spaces_base_url = cdn_endpoint.rstrip('/')
        elif origin_endpoint:
            self.do_spaces_base_url = origin_endpoint.rstrip('/')
        elif base_url_env:
            self.do_spaces_base_url = base_url_env.rstrip('/')
        elif self.storage_backend == 'do_spaces':
            self.do_spaces_base_url = f"https://{self.do_spaces_bucket}.{region}.digitaloceanspaces.com"
        elif self.storage_backend == 's3':
            self.do_spaces_base_url = f"https://{self.do_spaces_bucket}.s3.{region}.amazonaws.com"
        elif self.storage_backend == 'gcs':
            self.do_spaces_base_url = f"https://storage.googleapis.com/{self.do_spaces_bucket}"
        else:  # r2 has no public URL without a configured custom domain/base URL
            self.do_spaces_base_url = self.do_spaces_endpoint

        # Log configuration for debugging
        logger.debug(f"{self.storage_backend} bucket: {self.do_spaces_bucket}")
        logger.debug(f"{self.storage_backend} endpoint: {self.do_spaces_endpoint}")
        logger.debug(f"{self.storage_backend} base URL: {self.do_spaces_base_url}")

        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.do_spaces_endpoint,
                aws_access_key_id=self.do_spaces_key,
                aws_secret_access_key=self.do_spaces_secret,
                region_name=None if self.storage_backend in ('gcs', 'r2') else region,
                config=Config(signature_version='s3v4'),
            )
            logger.info(f"{self.storage_backend} client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize {self.storage_backend} client: {str(e)}")
            logger.error("Falling back to local storage...")
            self.storage_backend = 'local'

    def _init_azure_backend(self):
        """Configure the Azure Blob Storage client (separate SDK/API from S3)."""
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            logger.error(
                "STORAGE_BACKEND=azure_blob requires the 'azure-storage-blob' package "
                "(pip install azure-storage-blob). Falling back to local storage."
            )
            self.storage_backend = 'local'
            return

        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        account_url = os.getenv('AZURE_STORAGE_ACCOUNT_URL')
        account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
        self.azure_container = os.getenv('AZURE_STORAGE_CONTAINER')

        if not self.azure_container or not (connection_string or (account_url and account_key)):
            logger.error(
                "Azure Blob Storage requires AZURE_STORAGE_CONTAINER plus either "
                "AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL + "
                "AZURE_STORAGE_ACCOUNT_KEY. Falling back to local storage."
            )
            self.storage_backend = 'local'
            return

        try:
            if connection_string:
                service_client = BlobServiceClient.from_connection_string(connection_string)
            else:
                service_client = BlobServiceClient(account_url=account_url, credential=account_key)
            self.azure_container_client = service_client.get_container_client(self.azure_container)
            self.do_spaces_base_url = os.getenv(
                'AZURE_STORAGE_BASE_URL',
                f"{service_client.url.rstrip('/')}/{self.azure_container}",
            )
            logger.info("Azure Blob Storage client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob Storage client: {str(e)}")
            logger.error("Falling back to local storage...")
            self.storage_backend = 'local'

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------

    def _extract_bucket_and_key(self, url: str):
        """Extract bucket name and object key from any DigitalOcean Spaces URL.

        Handles the following patterns:
            • https://<bucket>.nyc3.digitaloceanspaces.com/<key>
            • https://<bucket>.nyc3.cdn.digitaloceanspaces.com/<key>
            • https://nyc3.digitaloceanspaces.com/<bucket>/<key> (path-style)

        Returns (bucket, key) or (None, None) if the URL does not look like a
        DO Spaces object link.
        """
        try:
            parsed = urlparse(url)
            host = parsed.netloc
            path = parsed.path.lstrip('/')  # remove leading slash

            # Style 1 & 2: bucket in subdomain
            m = re.match(r'^(?P<bucket>[A-Za-z0-9\-]+)\.nyc3(?:\.cdn)?\.digitaloceanspaces\.com$', host)
            if m:
                bucket = m.group('bucket')
                return bucket, path

            # Style 3: path style
            if host == 'nyc3.digitaloceanspaces.com':
                # first segment of path is bucket
                parts = path.split('/', 1)
                if len(parts) == 2:
                    bucket, key = parts
                    return bucket, key
        except Exception:
            pass
        return None, None

    def get_accessible_url(self, url: str, expires_in: int = 3600):
        """Ensure the supplied URL is publicly accessible.

        For objects stored in our DigitalOcean Spaces bucket, always return a
        presigned URL.  This avoids the situation where a HEAD request from our
        backend returns 200 (because we have credentials) but external services
        like Replicate later receive a 403.

        For any other URL that doesn't belong to our bucket we do a quick HEAD
        request – if that succeeds we assume the URL is already public and just
        return it.  Otherwise we simply return the original URL (caller may
        decide to upload it elsewhere).

        Note: the presign shortcut above only recognizes DO Spaces URL shapes
        (see _extract_bucket_and_key). Objects uploaded to the other
        S3_LIKE_BACKENDS or Azure fall through to the generic HEAD-request
        check below, which is sufficient as long as they're uploaded with
        the public-read ACL that upload_file()/save_url_to_storage() already
        set — presigning for private buckets on those backends isn't
        implemented since nothing in this codebase uses private buckets yet.
        """
        # If this is a DO Spaces object that we control, generate a presigned URL
        bucket, key = self._extract_bucket_and_key(url)

        # If this URL points to an object in any DO Spaces bucket we control we
        # want to serve a presigned URL so external services can fetch it even
        # if the object itself is private.  Workers may start with
        # STORAGE_BACKEND=local which means `self.s3_client` was *not*
        # initialised in __init__.  In that case we lazily create the client
        # here as long as the required DO credentials / endpoint env-vars are
        # present.
        if bucket and key:
            if not getattr(self, 's3_client', None):
                do_key = os.getenv('DO_SPACES_KEY')
                do_secret = os.getenv('DO_SPACES_SECRET')
                do_endpoint = os.getenv('DO_SPACES_ENDPOINT') or f"https://{bucket}.nyc3.digitaloceanspaces.com"
                if do_key and do_secret:
                    try:
                        self.s3_client = boto3.client(
                            's3',
                            endpoint_url=do_endpoint,
                            aws_access_key_id=do_key,
                            aws_secret_access_key=do_secret,
                            config=Config(signature_version='s3v4')
                        )
                        logger.info("Lazily initialised DO Spaces s3_client for presigning")
                    except Exception as init_err:
                        logger.error(f"Failed to lazily initialise s3_client: {init_err}")
            if getattr(self, 's3_client', None):
                try:
                    presigned = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=expires_in
                    )
                    logger.debug(
                        f"Generated presigned URL for {url} (expires in {expires_in}s)"
                    )
                    return presigned
                except Exception as e:
                    logger.error(
                        f"Failed to generate presigned URL for {url}: {e}; falling back to original URL"
                    )
                    # fall through to the public check below


        # Not our Spaces object – or presign failed – perform a lightweight HEAD
        try:
            head = requests.head(url, timeout=10, allow_redirects=True)
            if head.status_code == 200:
                return url
        except Exception:
            # We deliberately swallow the exception here; the original URL might
            # still be usable by the caller or get handled by a higher-level
            # fallback mechanism (e.g. tmpfiles.io upload).
            logger.debug(f"HEAD check failed for {url}; will return original URL anyway")

        return url  # fallback

    def save_url_to_storage(self, image_url, endpoint_type, filename=None, target_location=None):
        """
        Save image from URL to storage (local or DO Spaces)
        
        Args:
            image_url: URL of the image to download
            endpoint_type: Type of endpoint (character_generation, pose_generation, etc.)
            filename: Optional filename to use (default: random UUID)
            target_location: Optional target location override
            
        Returns:
            URL to the saved image
        """
        try:
            # Download the image 
            logger.info(f"Downloading image from: {image_url}")
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            
            # Generate filename if needed
            if not filename:
                filename = f"{uuid.uuid4()}.jpg"
            
            # First save locally as a fallback
            base_path = self.base_paths.get(endpoint_type, 'character_generation/output')
            
            # Override base path if target_location is specified
            if target_location:
                base_path = target_location
                
            local_path = os.path.join(self.local_base_path, base_path)
            os.makedirs(local_path, exist_ok=True)
            local_file_path = os.path.join(local_path, filename)
            
            with open(local_file_path, 'wb') as f:
                f.write(response.content)
            
            # Try to upload to the configured remote object store, if any
            if self.storage_backend in S3_LIKE_BACKENDS:
                try:
                    # Create object key
                    object_key = f"{base_path}/{filename}"
                    
                    # Upload directly from file 
                    with open(local_file_path, 'rb') as data:
                        self.s3_client.upload_fileobj(
                            data,
                            self.do_spaces_bucket,
                            object_key,
                            ExtraArgs={
                                'ACL': 'public-read',
                                'ContentType': response.headers.get('Content-Type', 'image/jpeg')
                            }
                        )
                    
                    # Construct DO Spaces URL
                    do_url = f"{self.do_spaces_base_url}/{object_key}"
                    logger.info(f"File uploaded to DO Spaces: {do_url}")
                    return do_url
                    
                except Exception as e:
                    logger.error(f"{self.storage_backend} upload failed: {str(e)}")
                    logger.info("Falling back to local storage")
            elif self.storage_backend == 'azure_blob':
                try:
                    object_key = f"{base_path}/{filename}"
                    with open(local_file_path, 'rb') as data:
                        self.azure_container_client.upload_blob(
                            name=object_key,
                            data=data,
                            overwrite=True,
                            content_type=response.headers.get('Content-Type', 'image/jpeg'),
                        )
                    azure_url = f"{self.do_spaces_base_url}/{object_key}"
                    logger.info(f"File uploaded to Azure Blob Storage: {azure_url}")
                    return azure_url
                except Exception as e:
                    logger.error(f"Azure Blob Storage upload failed: {str(e)}")
                    logger.info("Falling back to local storage")

            # Return local path if the remote upload failed or no remote backend is enabled
            return f"/media/{base_path}/{filename}"

        except Exception as e:
            logger.error(f"Error in save_url_to_storage: {str(e)}")
            # Return original URL as fallback
            return image_url

    def download_file(self, url, local_path=None):
        """
        Download a file from a URL or DO Spaces
        
        Args:
            url: URL to download
            local_path: Optional local path to save to
            
        Returns:
            Path to the downloaded file
        """
        try:
            # Generate a temp path if none provided
            if not local_path:
                filename = os.path.basename(urlparse(url).path)
                if not filename:
                    filename = f"{uuid.uuid4()}.file"
                local_path = os.path.join("/tmp", filename)
            
            # Check if URL belongs to any DO Spaces bucket (not just base_url)
            bucket, key = self._extract_bucket_and_key(url)
            if self.storage_backend in S3_LIKE_BACKENDS and bucket and key:
                try:
                    self.s3_client.download_file(bucket, key, local_path)
                    logger.info(f"File downloaded from DO Spaces: {local_path}")
                    return local_path
                except Exception as e:
                    logger.error(f"Error downloading from DO Spaces: {str(e)}")
                    logger.info("Falling back to HTTP download")
            
            # Regular HTTP download with intelligent fallback
            try:
                response = requests.get(url, timeout=60)
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                # If we got a 403 from the CDN, try generating a presigned URL (object may be private)
                if response is not None and response.status_code == 403 and self.storage_backend in S3_LIKE_BACKENDS and bucket and key:
                    logger.warning("403 Forbidden on direct GET – generating presigned URL and retrying")
                    try:
                        presigned_url = self.s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': bucket, 'Key': key},
                            ExpiresIn=3600,
                        )
                        response = requests.get(presigned_url, timeout=60)
                        response.raise_for_status()
                        # Switch url variable so downstream logging shows actual source
                        url = presigned_url
                    except Exception as presign_err:
                        logger.error(f"Presigned retry failed: {presign_err}")
                        raise http_err  # re-raise original error
                else:
                    raise

            # Save the file
            with open(local_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"File downloaded via HTTP: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return None

    def upload_file(
        self,
        file_input,
        endpoint_type,
        filename: str | None = None,
        subfolder: str | None = None,
        *,
        include_presigned: bool = False,
        presign_expires_in: int = 3600,
    ):
        """
        Upload a local file to storage
        
        Args:
            file_input: Path to the local file or file-like object
            endpoint_type: Type of endpoint (character_generation, pose_generation, etc.)
            filename: Optional filename to use (default: original filename)
            subfolder: Optional subfolder (e.g. per-job project folder) to prepend to the storage path
            include_presigned: Optional flag to return both public and presigned URLs
            presign_expires_in: Optional expiration time for presigned URL (default: 3600 seconds)
        
        Returns:
            URL to the uploaded file, or a dictionary with public and presigned URLs if include_presigned is True
        """
        try:
            is_file_object = hasattr(file_input, 'read')
            
            # If input is a file object, save it to a temp file first
            if is_file_object:
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_file_path = temp_file.name
                
                # Read content from the file object and write to temp file
                file_input.seek(0)
                temp_file.write(file_input.read())
                temp_file.close()
                
                # Use the temp file path for further operations
                file_path = temp_file_path
                
                # If no filename provided, use a UUID
                if not filename:
                    file_ext = '.jpg'  # Default extension
                    filename = f"{uuid.uuid4()}{file_ext}"
            else:
                # Input is a file path
                file_path = file_input
                # Use original filename if none provided
                if not filename:
                    filename = os.path.basename(file_path)
            
            # Determine base path based on endpoint type and optional subfolder
            base_path = self.base_paths.get(endpoint_type, 'character_generation/output')
            if subfolder:
                # Ensure we don't accidentally introduce double slashes
                subfolder = subfolder.strip('/\\')
                base_path = f"{base_path}/{subfolder}"
            
            # Copy to local storage as fallback
            local_output_path = os.path.join(self.local_base_path, base_path)
            os.makedirs(local_output_path, exist_ok=True)
            local_dest = os.path.join(local_output_path, filename)
            
            # Copy the file (read binary to handle all file types)
            with open(file_path, 'rb') as src, open(local_dest, 'wb') as dest:
                dest.write(src.read())
            
            # Try to upload to the configured remote object store, if any
            if self.storage_backend in S3_LIKE_BACKENDS:
                try:
                    # Determine content type
                    content_type = None
                    if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                        content_type = 'image/jpeg'
                    elif filename.lower().endswith('.png'):
                        content_type = 'image/png'
                    
                    # Create object key
                    object_key = f"{base_path}/{filename}"
                    
                    # Upload the file
                    with open(file_path, 'rb') as data:
                        self.s3_client.upload_fileobj(
                            data,
                            self.do_spaces_bucket,
                            object_key,
                            ExtraArgs={
                                'ACL': 'public-read',
                                'ContentType': content_type or 'application/octet-stream'
                            }
                        )
                    
                    # Construct DO Spaces URL
                    do_url = f"{self.do_spaces_base_url}/{object_key}"
                    logger.info(f"File uploaded to DO Spaces: {do_url}")
                    
                    # Clean up temp file if we created one
                    if is_file_object and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                        
                    # ------------------------------------------------------------------
                    # Optionally return both public and presigned URL ------------------
                    # ------------------------------------------------------------------
                    if include_presigned:
                        try:
                            presigned = self.s3_client.generate_presigned_url(
                                "get_object",
                                Params={"Bucket": self.do_spaces_bucket, "Key": object_key},
                                ExpiresIn=presign_expires_in,
                            )
                        except Exception:
                            presigned = do_url  # graceful fallback
                        return {
                            "public_url": do_url,
                            "presigned_url": presigned,
                        }
                    
                    return do_url
                    
                except Exception as e:
                    logger.error(f"{self.storage_backend} upload failed: {str(e)}")
                    logger.info("Falling back to local storage")
            elif self.storage_backend == 'azure_blob':
                try:
                    content_type = None
                    if filename.lower().endswith(('.jpg', '.jpeg')):
                        content_type = 'image/jpeg'
                    elif filename.lower().endswith('.png'):
                        content_type = 'image/png'

                    object_key = f"{base_path}/{filename}"
                    with open(file_path, 'rb') as data:
                        self.azure_container_client.upload_blob(
                            name=object_key,
                            data=data,
                            overwrite=True,
                            content_type=content_type or 'application/octet-stream',
                        )
                    azure_url = f"{self.do_spaces_base_url}/{object_key}"
                    logger.info(f"File uploaded to Azure Blob Storage: {azure_url}")

                    if is_file_object and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

                    if include_presigned:
                        # Azure Blob Storage SAS-token presigning isn't implemented;
                        # both fields point at the same public blob URL.
                        return {"public_url": azure_url, "presigned_url": azure_url}
                    return azure_url
                except Exception as e:
                    logger.error(f"Azure Blob Storage upload failed: {str(e)}")
                    logger.info("Falling back to local storage")

            # Clean up temp file if we created one
            if is_file_object and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

            local_url = f"/media/{base_path}/{filename}"
            if include_presigned:
                # For local backend we simply duplicate the URL fields
                return {"public_url": local_url, "presigned_url": local_url}
            
            return local_url
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return None
            
    def get_public_url(self, object_key):
        """
        Get a public URL for an object in storage
        
        Args:
            object_key: The object key or path in storage
            
        Returns:
            URL to the object
        """
        try:
            # For any S3-compatible or Azure backend, construct the URL from base_url
            if self.storage_backend in S3_LIKE_BACKENDS or self.storage_backend == 'azure_blob':
                # Ensure no leading slash to avoid double slashes in the URL
                if object_key.startswith('/'):
                    object_key = object_key[1:]

                return f"{self.do_spaces_base_url}/{object_key}"
            else:
                # For local storage, just return a media URL
                if object_key.startswith('/'):
                    return object_key
                else:
                    return f"/media/{object_key}"
        except Exception as e:
            logger.error(f"Error getting public URL: {str(e)}")
            return None

# Singleton instance for easy import
storage_client = StorageClient()