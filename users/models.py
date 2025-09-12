from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import os
from django.conf import settings
from django.utils import timezone


class RecruiterManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        if not first_name:
            raise ValueError('First name must be provided')
        if not last_name:
            raise ValueError('Last name must be provided')
            
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
        
    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self.create_user(email, first_name, last_name, password, **extra_fields)

class Recruiter(AbstractUser):
    username = None
    email = models.EmailField(_('email_address'), unique=True)    
    first_name = models.CharField(_('first name'), max_length=100, blank=False, null=False)
    last_name = models.CharField(_('last name'), max_length=100, blank=False, null=False)
    image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_expires = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = RecruiterManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name'] 
    
    def is_verification_code_valid(self, code):
        return (
            self.verification_code == code and 
            self.verification_code_expires and 
            self.verification_code_expires > timezone.now()
        )
    
    def __str__(self):
        return f"Name:{self.first_name} {self.last_name} \n Id:{self.id}"  
 

Recruiter = get_user_model()

class OdooCredentials(models.Model):
    credentials_id = models.AutoField(primary_key=True)
    odoo_user_id = models.IntegerField()
    recruiter = models.ForeignKey(Recruiter, on_delete=models.CASCADE, related_name='odoo_credentials')
    api_key = models.TextField() 
    email_address = models.TextField()
    db_name = models.TextField()
    db_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('recruiter', 'db_name', 'odoo_user_id')
    
    def __str__(self):
        return f"{self.recruiter.email} - {self.db_name}"
    
    def save(self, *args, **kwargs):
        if self.api_key:
            if not self.pk or self._is_api_key_changed():
                self.api_key = self._encrypt_api_key(self.api_key)
        super().save(*args, **kwargs)
    
    def _is_api_key_changed(self):
        if not self.pk:
            return True 
        try:
            current = OdooCredentials.objects.get(pk=self.pk)
            return current.api_key != self.api_key
        except OdooCredentials.DoesNotExist:
            return True
        
    def _encrypt_api_key(self, api_key):
        if not api_key:
            return ""
        key = self._get_valid_encryption_key()
        iv = os.urandom(16)
        cipher = AES.new(key, AES.MODE_CBC, iv) 
        padded_data = pad(api_key.encode(), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        return base64.b64encode(iv + encrypted_data).decode('utf-8')
    
    def _get_valid_encryption_key(self):
        key = settings.ODOO_API_ENCRYPTION_KEY
        if len(key) > 32:
            import hashlib
            return hashlib.sha256(key.encode()).digest()
        elif len(key) in [16, 24]:
            return key.encode()
        else:
            return key.ljust(32, '\0').encode()
    
    def _decrypt_api_key(self, encrypted_api_key):
        if not encrypted_api_key:
            return ""
        
        try:
            encrypted_data = base64.b64decode(encrypted_api_key)
            iv = encrypted_data[:16]
            encrypted = encrypted_data[16:]
            key = self._get_valid_encryption_key()
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_data = unpad(cipher.decrypt(encrypted), AES.block_size)
            
            return decrypted_data.decode('utf-8')
        except Exception as e:
            print(f"Error decrypting API key: {str(e)}")
            return ""
    
    def get_api_key(self):
        return self._decrypt_api_key(self.api_key)