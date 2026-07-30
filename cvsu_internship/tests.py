from django.test import SimpleTestCase

from cvsu_internship.storage import SmartCloudinaryMediaStorage


class SmartCloudinaryMediaStorageTests(SimpleTestCase):
    def test_detects_image_files_as_images(self):
        storage = SmartCloudinaryMediaStorage()
        self.assertEqual(storage._get_resource_type('profile.png'), 'image')
        self.assertEqual(storage._get_resource_type('photo.jpg'), 'image')

    def test_detects_documents_as_raw_files(self):
        storage = SmartCloudinaryMediaStorage()
        self.assertEqual(storage._get_resource_type('document.pdf'), 'raw')
        self.assertEqual(storage._get_resource_type('report.docx'), 'raw')

    def test_detects_video_files_as_video(self):
        storage = SmartCloudinaryMediaStorage()
        self.assertEqual(storage._get_resource_type('clip.mp4'), 'video')
