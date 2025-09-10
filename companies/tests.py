from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db import transaction
from users.models import Recruiter
from .models import Company

class CompanyModelTests(TestCase):
    def setUp(self):
        self.recruiter = Recruiter.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        
        self.recruiter2 = Recruiter.objects.create_user(
            email='another@example.com',
            first_name='Jane',
            last_name='Smith',
            password='testpass123'
        )
        
        self.company_data = {
            'company_name': 'Test Company',
            'recruiter': self.recruiter
        }

    def test_create_company(self):
        company = Company.objects.create(**self.company_data)
        self.assertEqual(company.company_name, 'Test Company')
        self.assertEqual(company.recruiter, self.recruiter)
        self.assertIsNotNone(company.company_id) 
        self.assertIsNone(company.odoo_company_id)  

    def test_string_representation(self):
        company = Company.objects.create(**self.company_data)
        self.assertEqual(str(company), company.company_name)

    def test_unique_together_constraint_duplicate(self):
        Company.objects.create(**self.company_data)
        
        with self.assertRaises(IntegrityError):
            Company.objects.create(**self.company_data)

    def test_unique_together_constraint_different_recruiter(self):
        Company.objects.create(**self.company_data)
        
        company2 = Company.objects.create(
            company_name='Test Company',
            recruiter=self.recruiter2
        )
        
        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(company2.company_name, 'Test Company')
        self.assertEqual(company2.recruiter, self.recruiter2)

    def test_unique_together_constraint_different_name(self):
        Company.objects.create(**self.company_data)
        
        company2 = Company.objects.create(
            company_name='Another Company',
            recruiter=self.recruiter
        )
        
        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(company2.company_name, 'Another Company')
        self.assertEqual(company2.recruiter, self.recruiter)

    def test_foreign_key_relationship(self):
        company = Company.objects.create(**self.company_data)
        
        self.assertEqual(company.recruiter, self.recruiter)
        
        self.assertIn(company, self.recruiter.companies.all())
        self.assertEqual(self.recruiter.companies.count(), 1)
        
        company2 = Company.objects.create(
            company_name='Another Company',
            recruiter=self.recruiter
        )
        
        self.assertIn(company, self.recruiter.companies.all())
        self.assertIn(company2, self.recruiter.companies.all())
        self.assertEqual(self.recruiter.companies.count(), 2)

    def test_odoo_company_id_field(self):
        company = Company.objects.create(**self.company_data)
        self.assertIsNone(company.odoo_company_id)
        
        company.odoo_company_id = 12345
        company.save()
        self.assertEqual(company.odoo_company_id, 12345)
        
        company.odoo_company_id = None
        company.save()
        self.assertIsNone(company.odoo_company_id)

    def test_timestamps(self):
        company = Company.objects.create(**self.company_data)
        
        self.assertIsNotNone(company.created_at)
        
        self.assertIsNotNone(company.updated_at)
        
        original_updated_at = company.updated_at
        company.company_name = 'Updated Company'
        company.save()
        
        company.refresh_from_db()
        
        self.assertNotEqual(company.updated_at, original_updated_at)
        self.assertGreater(company.updated_at, original_updated_at)

    def test_company_name_max_length(self):
        long_name = 'a' * 100
        company = Company.objects.create(
            company_name=long_name,
            recruiter=self.recruiter
        )
        self.assertEqual(company.company_name, long_name)
        
        too_long_name = 'a' * 101
        with self.assertRaises(ValidationError):
            company = Company(
                company_name=too_long_name,
                recruiter=self.recruiter
            )
            company.full_clean()  

    def test_cascade_delete(self):
        company = Company.objects.create(**self.company_data)
        
        self.assertTrue(Company.objects.filter(pk=company.pk).exists())
        
        self.recruiter.delete()
        
        self.assertFalse(Company.objects.filter(pk=company.pk).exists())

    def test_company_name_required(self):
        with self.assertRaises(ValidationError):
            company = Company(
                company_name='',
                recruiter=self.recruiter
            )
            company.full_clean()
    def test_recruiter_required(self):
        with self.assertRaises(IntegrityError):
            Company.objects.create(
                company_name='Test Company',
                recruiter=None
            )