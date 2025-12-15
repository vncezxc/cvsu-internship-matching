from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class MediaStorage(S3Boto3Storage):
    """
    Custom storage backend for DigitalOcean Spaces.
    Prevents bucket name from being added to file paths.
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
        
        return name
    
    def url(self, name, parameters=None, expire=None, http_method=None):
        """
        Override URL generation to use CDN domain directly.
        """
        if self.custom_domain:
            # Normalize the name first
            name = self._normalize_name(name)
            # Use CDN domain directly
            url = f"https://{self.custom_domain}/{name}"
            return url
        
        # Fallback to default behavior
        return super().url(name, parameters, expire, http_method)