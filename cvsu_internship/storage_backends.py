# storage_backends.py
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings
import os


class MediaStorage(S3Boto3Storage):
    """
    Custom storage backend for DigitalOcean Spaces.
    Ensures files are stored directly in the bucket without extra folders.
    """
    location = ''  # CRITICAL: Must be empty
    default_acl = 'public-read'
    file_overwrite = False
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN
    
    def __init__(self, *args, **kwargs):
        """Initialize storage and ensure location is empty."""
        super().__init__(*args, **kwargs)
        # Force location to be empty to prevent path prefix issues
        self.location = ''
    
    def _normalize_name(self, name):
        """
        Override to prevent bucket name from being added to path.
        This is the KEY fix to prevent cvsu-internship-moa/cvsu-internship-moa/
        """
        # Remove any leading slashes
        name = name.lstrip('/')
        
        # Remove bucket name if it's at the start of the path
        bucket_prefix = f"{settings.AWS_STORAGE_BUCKET_NAME}/"
        if name.startswith(bucket_prefix):
            name = name[len(bucket_prefix):]
        
        # Remove media/ prefix if it exists (we want files directly in bucket root)
        if name.startswith('media/'):
            name = name[5:]  # Remove 'media/' prefix
            
        # Remove any duplicate bucket names
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        # Handle cases like bucket-name/bucket-name/path
        double_prefix = f"{bucket_name}/{bucket_name}/"
        if name.startswith(double_prefix):
            name = name[len(bucket_name) + 1:]  # Remove first bucket name
        
        return name
    
    def _save(self, name, content):
        """Override save to ensure proper path handling."""
        # Normalize the name before saving
        name = self._normalize_name(name)
        # Debug log: print the final path being saved
        import logging
        logger = logging.getLogger("django.storage")
        logger.warning(f"[MediaStorage] Saving file to: {name}")
        return super()._save(name, content)
    
    def url(self, name, parameters=None, expire=None, http_method=None):
        """
        Override URL generation to use CDN domain directly.
        """
        # Normalize the name first
        name = self._normalize_name(name)
        
        if self.custom_domain:
            # Use CDN domain directly
            url = f"https://{self.custom_domain}/{name}"
            return url
        
        # Fallback to default behavior
        return super().url(name, parameters, expire, http_method)
    
    def get_available_name(self, name, max_length=None):
        """Ensure we get a clean name without bucket prefixes."""
        name = self._normalize_name(name)
        return super().get_available_name(name, max_length)