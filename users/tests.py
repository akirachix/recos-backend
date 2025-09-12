from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from users.models import OdooCredentials
from unittest.mock import patch

User = get_user_model()

class OdooCredentialsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
        self.odoo_data = {
            'odoo_user_id': 123,
            'recruiter': self.user,
            'api_key': 'test_api_key',
            'email_address': 'odoo@example.com',
            'db_name': 'test_db',
            'db_url': 'https://test.odoo.com'
        }

    @override_settings(ODOO_API_ENCRYPTION_KEY='this_is_a_test_key_for_encryption_32bytes')
    def test_string_representation(self):
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        self.assertEqual(str(credentials), f"{self.user.email} - {credentials.db_name}")

    @override_settings(ODOO_API_ENCRYPTION_KEY='this_is_a_test_key_for_encryption_32bytes')
    def test_api_key_encryption(self):
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        self.assertNotEqual(credentials.api_key, 'test_api_key')
        self.assertEqual(credentials.get_api_key(), 'test_api_key')

    @override_settings(ODOO_API_ENCRYPTION_KEY='this_is_a_test_key_for_encryption_32bytes')
    def test_api_key_encryption_on_update(self):
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        original_encrypted_key = credentials.api_key
        
        credentials.api_key = 'new_api_key'
        credentials.save()
        
        self.assertNotEqual(credentials.api_key, original_encrypted_key)
        self.assertEqual(credentials.get_api_key(), 'new_api_key')

    @override_settings(ODOO_API_ENCRYPTION_KEY='this_is_a_test_key_for_encryption_32bytes')
    def test_api_key_decryption_failure(self):
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        
        credentials.api_key = "corrupted_encrypted_data"
        
        self.assertEqual(credentials.get_api_key(), "")

    @override_settings(ODOO_API_ENCRYPTION_KEY='short_key')
    def test_short_encryption_key_handling(self):
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        self.assertEqual(str(credentials), f"{self.user.email} - {credentials.db_name}")

    @override_settings(ODOO_API_ENCRYPTION_KEY='this_key_is_longer_than_32_bytes_and_should_be_hashed')
    def test_long_encryption_key_handling(self):
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        self.assertEqual(str(credentials), f"{self.user.email} - {credentials.db_name}")

    @patch('users.models.OdooCredentials._encrypt_api_key')
    @patch('users.models.OdooCredentials._decrypt_api_key')
    def test_encryption_methods_called(self, mock_decrypt, mock_encrypt):
        mock_encrypt.return_value = 'encrypted_api_key'
        mock_decrypt.return_value = 'test_api_key'
        
        credentials = OdooCredentials.objects.create(**self.odoo_data)
        
        mock_encrypt.assert_called_with('test_api_key')
        
        credentials.get_api_key()
        mock_decrypt.assert_called_with('encrypted_api_key')