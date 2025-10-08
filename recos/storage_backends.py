import os
import mimetypes
from urllib.parse import quote
from django.core.files.storage import Storage
from django.core.files.base import ContentFile, File
from supabase import create_client, Client
from django.conf import settings

class SupabaseStorage(Storage):
    """
    A Django storage backend for Supabase Storage.
    """
    def __init__(self, *args, **kwargs):
        self.supabase_url: str = settings.SUPABASE_URL
        self.supabase_key: str = settings.SUPABASE_SERVICE_ROLE_KEY
        self.bucket_name: str = settings.SUPABASE_BUCKET_NAME
        self.client: Client = create_client(self.supabase_url, self.supabase_key)

    def _open(self, name, mode='rb'):
        """
        Retrieves the specified file from Supabase Storage.
        """
        try:
            response = self.client.storage.from_(self.bucket_name).download(name)
            return File(ContentFile(response))
        except Exception as e:
            raise FileNotFoundError(f"No Supabase object found: {name}")

    def _save(self, name, content):
        """
        Saves new content to the file specified by name.
        The name will be used as the object path in the bucket.
        """
        content.seek(0)
        
        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        
        options = {
            'content-type': content_type
        }
        
        try:
            self.client.storage.from_(self.bucket_name).upload(
                path=name, 
                file=content.read(), 
                file_options=options
            )
        except Exception as e:
            raise
        
        return name

    def exists(self, name):
        """
        Returns True if a file referred to by the given name already exists in the
        storage system, or False if the name is available for a new file.
        """
        try:
            self.client.storage.from_(self.bucket_name).get_public_url(name)
            return True
        except Exception:
            return False

    def url(self, name):
        """
        Returns the absolute URL where the file's contents can be accessed
        directly by a Web browser.
        """
        try:
            return self.client.storage.from_(self.bucket_name).get_public_url(name)

        except Exception as e:
            return None

    def delete(self, name):
        """
        Deletes the specified file.
        """
        try:
            self.client.storage.from_(self.bucket_name).remove([name])
        except Exception as e:
            raise