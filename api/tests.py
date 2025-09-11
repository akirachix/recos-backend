from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from job.models import  Job
from candidate.models import Candidate
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
from rest_framework.authtoken.models import Token
from unittest.mock import patch, MagicMock
from users.models import Recruiter
from ai_reports.models import AIReport

class APITests(APITestCase):

    def setUp(self):
        self.job = Job.objects.create(
            job_title="API Test Job",
            job_description="Test Desc",
            generated_job_summary="Summary",
            expired_at="2099-12-31T23:59:59Z",
        )
        self.candidate = Candidate.objects.create(
            name="API Candidate",
            email="api@example.com",
            job=self.job,
            generated_skill_summary="Skill Summary"
        )

    def test_job_list(self):
        url = reverse('job-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_candidate_list(self):
        url = reverse('candidate-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


User = get_user_model()

class RecruiterRegistrationViewTests(APITestCase):
    def test_register_recruiter(self):
        url = reverse('register')
        data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)

class RecruiterListViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            first_name='Staff',
            last_name='User',
            password='testpass123',
            is_staff=True
        )
        self.token = Token.objects.create(user=self.user)
        self.staff_token = Token.objects.create(user=self.staff_user)

    def test_list_recruiters_as_user(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        url = reverse('recruiter_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.user.id)

    def test_list_recruiters_as_staff(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.staff_token.key)
        url = reverse('recruiter_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  

class LoginViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )

    def test_login_success(self):
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)

    def test_login_invalid_credentials(self):
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class VerifyOdooAccountTests(APITestCase):
    @patch('api.views.OdooService')
    def test_verify_odoo_account_success(self, mock_odoo_service):
        mock_service_instance = MagicMock()
        mock_service_instance.authenticate.return_value = True
        mock_odoo_service.return_value = mock_service_instance
        
        url = reverse('verify_odoo_account')
        data = {
            'db_url': 'https://test.odoo.com',
            'db_name': 'test_db',
            'email': 'odoo@example.com',
            'api_key': 'test_api_key'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])

class LogoutViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        url = reverse('logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Logout successful')

class AddOdooCredentialsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        
        content_type = ContentType.objects.get_for_model(User)
        permission, created = Permission.objects.get_or_create(
            codename='ass_odoocredentials',
            content_type=content_type,
            defaults={'name': 'Can add Odoo credentials'}
        )
        
        self.user.user_permissions.add(permission)

    @patch('api.views.OdooService')
    def test_add_odoo_credentials_success(self, mock_odoo_service):
        mock_service_instance = MagicMock()
        mock_service_instance.authenticate.return_value = True
        mock_service_instance.get_user_info.return_value = [{'id': 123}]
        mock_service_instance.get_companies.return_value = [{'id': 1, 'name': 'Test Company'}]
        mock_odoo_service.return_value = mock_service_instance
        
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        url = reverse('add_odoo_credentials')
        data = {
            'db_url': 'https://test.odoo.com',
            'db_name': 'test_db',
            'email': 'odoo@example.com',
            'api_key': 'test_api_key'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('credentials', response.data)

class GetOdooCredentialsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_get_odoo_credentials(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        url = reverse('get_odoo_credentials')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

class GetCompaniesTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_get_companies(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        url = reverse('get_companies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

class ForgotPasswordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )

    @patch('api.views.send_mail')
    @patch('api.views.render_to_string')
    def test_forgot_password_success(self, mock_render_to_string, mock_send_mail):
        mock_render_to_string.return_value = "Mocked email content"
        
        url = reverse('forgot_password')
        data = {'email': 'test@example.com'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(mock_send_mail.called)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.verification_code)

class ResetPasswordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.user.verification_code = '123456'
        self.user.verification_code_expires = timezone.now() + timedelta(minutes=15)
        self.user.save()

    def test_reset_password_success(self):
        url = reverse('reset_password')
        data = {
            'email': 'test@example.com',
            'code': '123456',
            'new_password': 'newpass123',
            'confirm_password': 'newpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.verification_code)

class VerifyResetCodeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.user.verification_code = '123456'
        self.user.verification_code_expires = timezone.now() + timedelta(minutes=15)
        self.user.save()

    def test_verify_reset_code_success(self):
        url = reverse('verify_reset_code')
        data = {
            'email': 'test@example.com',
            'code': '123456'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])

    def test_verify_reset_code_invalid(self):
        url = reverse('verify_reset_code')
        data = {
            'email': 'test@example.com',
            'code': '654321'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['valid'])
class AIReportAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.dummy_conversation_id = 1

    def test_create_ai_report(self):
        url = reverse('ai-report-list')
        data = {
            'conversation_id': self.dummy_conversation_id,
            'skill_match_score': 90.0,
            'final_match_score': 95.5,
            'strengths': 'Great communicator',
            'weaknesses': 'New to Python',
            'overall_recommendation': 'Hire',
            'skills_breakdown': {"Python": 80, "Django": 70},
            'initial_analysis': {"Python": 30, "Problem Solving": 45},
            'performance_analysis': {"Attention to Detail": "High"}
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AIReport.objects.count(), 1)
        self.assertEqual(AIReport.objects.first().skill_match_score, 90.0)
        self.assertEqual(AIReport.objects.first().final_match_score, 95.5)
        self.assertEqual(AIReport.objects.first().skills_breakdown, {"Python": 80, "Django": 70})

    def test_generate_report_creates_new(self):
        url = reverse('ai-report-generate-report')
        data = {'conversation_id': self.dummy_conversation_id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AIReport.objects.filter(conversation_id=self.dummy_conversation_id).exists()
        )
        report = AIReport.objects.get(conversation_id=self.dummy_conversation_id)
        self.assertIsInstance(report.skills_breakdown, dict)
        self.assertIsInstance(report.initial_analysis, dict)
        self.assertIsInstance(report.performance_analysis, dict)

    def test_generate_report_fails_if_exists(self):
        AIReport.objects.create(
            conversation_id=self.dummy_conversation_id,
            skill_match_score=85.0,
            final_match_score=90.0,
            strengths='Strength',
            weaknesses='Weakness',
            overall_recommendation='Recommend',
            skills_breakdown={"Python": 90},
            initial_analysis={"Python": 40},
            performance_analysis={"Attention": "Medium"}
        )
        url = reverse('ai-report-generate-report')
        data = {'conversation_id': self.dummy_conversation_id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('AI report already exists', response.data.get('error', ''))

    def test_get_by_conversation(self):
        report = AIReport.objects.create(
            conversation_id=self.dummy_conversation_id,
            skill_match_score=88.5,
            final_match_score=90.3,
            strengths='Strength',
            weaknesses='Weakness',
            overall_recommendation='Recommend',
            skills_breakdown={"Python": 80},
            initial_analysis={"Python": 30},
            performance_analysis={"Attention": "High"}
        )
        url = reverse('ai-report-by-conversation', kwargs={'conversation_id': self.dummy_conversation_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['report_id'], report.report_id)

    def test_update_score(self):
        report = AIReport.objects.create(
            conversation_id=self.dummy_conversation_id,
            skill_match_score=75.0,
            final_match_score=80.0,
            strengths='Strength',
            weaknesses='Weakness',
            overall_recommendation='Recommend',
            skills_breakdown={"Python": 80},
            initial_analysis={"Python": 30},
            performance_analysis={"Attention": "High"}
        )
        url = reverse('ai-report-update-score', kwargs={'pk': report.report_id})
        data = {'skill_match_score': 92.5}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.skill_match_score, 92.5)

    def test_update_score_invalid(self):
        report = AIReport.objects.create(
            conversation_id=self.dummy_conversation_id,
            skill_match_score=75.0,
            final_match_score=80.0,
            strengths='Strength',
            weaknesses='Weakness',
            overall_recommendation='Recommend',
            skills_breakdown={"Python": 80},
            initial_analysis={"Python": 30},
            performance_analysis={"Attention": "High"}
        )
        url = reverse('ai-report-update-score', kwargs={'pk': report.report_id})
        data = {'skill_match_score': 150.0}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('skill_match_score must be a valid number', str(response.data))
