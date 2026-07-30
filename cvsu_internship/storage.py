import os

import cloudinary
from cloudinary_storage.storage import MediaCloudinaryStorage


class SmartCloudinaryMediaStorage(MediaCloudinaryStorage):
    """Upload files using the right Cloudinary resource type."""

    def _get_resource_type(self, name, content=None):
        content_type = None
        if content is not None:
            content_type = getattr(content, 'content_type', None)
            if not content_type and hasattr(content, 'file'):
                content_type = getattr(content.file, 'content_type', None)
        if content_type:
            content_type = content_type.lower()
            if content_type.startswith('image/'):
                return 'image'
            if content_type.startswith('video/'):
                return 'video'

        extension = os.path.splitext(name)[1].lower()
        if extension in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg'}:
            return 'image'
        if extension in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}:
            return 'video'
        return 'raw'

    def _upload(self, name, content):
        resource_type = self._get_resource_type(name, content)
        options = {'use_filename': True, 'resource_type': resource_type, 'tags': self.TAG}
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        return cloudinary.uploader.upload(content, **options)
