from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings
from unittest.mock import patch
import datetime

Recruiter = get_user_model()

class RecruiterModelTests(TestCase):
    def setUp(self):
        self.recruiter_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'testpass123'
        }

    def test_create_recruiter(self):
        recruiter = Recruiter.objects.create_user(
            email=self.recruiter_data['email'],
            first_name=self.recruiter_data['first_name'],
            last_name=self.recruiter_data['last_name'],
            password=self.recruiter_data['password']
        )
        self.assertEqual(recruiter.email, 'test@example.com')
        self.assertEqual(recruiter.first_name, 'John')
        self.assertEqual(recruiter.last_name, 'Doe')
        self.assertTrue(recruiter.is_active)
        self.assertFalse(recruiter.is_staff)
        self.assertFalse(recruiter.is_superuser)

    def test_email_is_unique(self):
        Recruiter.objects.create_user(
            email=self.recruiter_data['email'],
            first_name=self.recruiter_data['first_name'],
            last_name=self.recruiter_data['last_name'],
            password=self.recruiter_data['password']
        )
        with self.assertRaises(Exception):
            Recruiter.objects.create_user(
                email=self.recruiter_data['email'],
                first_name=self.recruiter_data['first_name'],
                last_name=self.recruiter_data['last_name'],
                password=self.recruiter_data['password']
            )

    def test_create_recruiter_no_email(self):
        with self.assertRaises(ValueError):
            Recruiter.objects.create_user(
                email='',
                first_name='John',
                last_name='Doe',
                password='testpass123'
            )

    def test_verification_code_valid(self):
        recruiter = Recruiter.objects.create_user(
            email=self.recruiter_data['email'],
            first_name=self.recruiter_data['first_name'],
            last_name=self.recruiter_data['last_name'],
            password=self.recruiter_data['password']
        )
        
        recruiter.verification_code = '123456'
        recruiter.verification_code_expires = timezone.now() + datetime.timedelta(minutes=10)
        recruiter.save()
        
        self.assertTrue(recruiter.is_verification_code_valid('123456'))
        self.assertFalse(recruiter.is_verification_code_valid('654321'))
        
        recruiter.verification_code_expires = timezone.now() - datetime.timedelta(minutes=10)
        recruiter.save()
        self.assertFalse(recruiter.is_verification_code_valid('123456'))

    def test_string_representation(self):
        recruiter = Recruiter.objects.create_user(
            email=self.recruiter_data['email'],
            first_name=self.recruiter_data['first_name'],
            last_name=self.recruiter_data['last_name'],
            password=self.recruiter_data['password']
        )
        
        expected_str = f"Name:{recruiter.first_name} {recruiter.last_name} \n Id:{recruiter.id}"
        
        print(f"Recruiter email: {recruiter.email}")
        print(f"Recruiter string representation: {str(recruiter)}")
        print(f"Expected string representation: {expected_str}")
        print(f"Recruiter class: {recruiter.__class__}")
        print(f"Recruiter MRO: {recruiter.__class__.__mro__}")
        
        import inspect
        for cls in recruiter.__class__.__mro__:
            if '__str__' in cls.__dict__:
                try:
                    source = inspect.getsource(cls.__str__)
                    print(f"Found __str__ in {cls.__name__}: {source}")
                except (TypeError, OSError):
                    print(f"Found __str__ in {cls.__name__}: [built-in method]")
        
        self.assertEqual(str(recruiter), expected_str)


class OdooCredentialsModelTests(TestCase):
    def setUp(self):
        self.recruiter = Recruiter.objects.create_user(
            email='recruiter@example.com',
            first_name='Jane',
            last_name='Smith',
            password='testpass123'
        )
        self.odoo_data = {
            'recruiter': self.recruiter,
            'odoo_user_id': 123,
            'api_key': 'test_api_key',
            'email_address': 'odoo@example.com',
            'db_name': 'test_db',
            'db_url': 'https://test.odoo.com'
        }

    @override_settings(ODOO_API_ENCRYPTION_KEY='test_encryption_key_32_bytes')
    def test_create_odoo_credentials(self):
        from .models import OdooCredentials          
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        self.assertEqual(credentials.recruiter, self.recruiter)
        self.assertEqual(credentials.odoo_user_id, 123)
        self.assertEqual(credentials.email_address, 'odoo@example.com')
        self.assertEqual(credentials.db_name, 'test_db')
        self.assertEqual(credentials.db_url, 'https://test.odoo.com')
        self.assertNotEqual(credentials.api_key, 'test_api_key')  # Should be encrypted

    @override_settings(ODOO_API_ENCRYPTION_KEY='test_encryption_key_32_bytes')
    def test_api_key_encryption(self):
        from .models import OdooCredentials
        
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        
        self.assertNotEqual(credentials.api_key, 'test_api_key')
        
        decrypted_key = credentials.get_api_key()
        self.assertEqual(decrypted_key, 'test_api_key')

    @override_settings(ODOO_API_ENCRYPTION_KEY='test_encryption_key_32_bytes')
    def test_api_key_only_encrypted_on_change(self):
        from .models import OdooCredentials
        
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        original_encrypted = credentials.api_key
        
        credentials.db_name = 'new_db_name'
        credentials.save()
        self.assertEqual(credentials.api_key, original_encrypted)
        
        credentials.api_key = 'new_api_key'
        credentials.save()
        self.assertNotEqual(credentials.api_key, original_encrypted)
        self.assertEqual(credentials.get_api_key(), 'new_api_key')

    @override_settings(ODOO_API_ENCRYPTION_KEY='short_key')
    def test_short_encryption_key_handling(self):
        from .models import OdooCredentials
        
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        
        decrypted_key = credentials.get_api_key()
        self.assertEqual(decrypted_key, 'test_api_key')
        expected_key = 'short_key'.ljust(32, '\0').encode()
        self.assertEqual(len(expected_key), 32)

    @override_settings(ODOO_API_ENCRYPTION_KEY='exactly_16_bytes_key')
    def test_16_byte_encryption_key(self):
        from .models import OdooCredentials
        
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        decrypted_key = credentials.get_api_key()
        self.assertEqual(decrypted_key, 'test_api_key')

    def test_string_representation(self):
        from .models import OdooCredentials
        
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        expected_str = f"{self.recruiter.email} - {self.odoo_data['db_name']}"
        self.assertEqual(str(credentials), expected_str)

    @override_settings(ODOO_API_ENCRYPTION_KEY='test_encryption_key_32_bytes')
    def test_empty_api_key_handling(self):
        from .models import OdooCredentials
        
        self.odoo_data['api_key'] = ''
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        self.assertEqual(credentials.get_api_key(), '')

    @override_settings(ODOO_API_ENCRYPTION_KEY='test_encryption_key_32_bytes')
    def test_decryption_error_handling(self):
        from .models import OdooCredentials
        
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        OdooCredentials.objects.filter(pk=credentials.pk).update(api_key='corrupted_data')
        
        credentials.refresh_from_db()
        self.assertEqual(credentials.get_api_key(), '')