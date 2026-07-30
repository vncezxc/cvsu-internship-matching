import os

from cloudinary_storage.storage import MediaCloudinaryStorage


class SmartCloudinaryMediaStorage(MediaCloudinaryStorage):
    """Upload files using the right Cloudinary resource type."""

    def _get_resource_type(self, name):
        extension = os.path.splitext(name)[1].lower()
        if extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg'}:
            return 'image'
        if extension in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}:
            return 'video'
        return 'raw'
