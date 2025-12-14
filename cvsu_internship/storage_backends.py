from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class MediaStorage(S3Boto3Storage):
    """
    Custom storage backend for DigitalOcean Spaces.
    Uses CDN domain for file URLs to avoid bucket name duplication.
    """
    location = ''
    default_acl = 'public-read'
    file_overwrite = False
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN
    
    def url(self, name, parameters=None, expire=None, http_method=None):
        """
        Override URL generation to use CDN domain directly.
        This prevents the bucket name from being duplicated in URLs.
        """
        if self.custom_domain:
            # Use CDN domain directly
            url = f"https://{self.custom_domain}/{name}"
            return url
        
        # Fallback to default behavior
        return super().url(name, parameters, expire, http_method)