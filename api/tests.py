from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from job.models import  Job
from candidate.models import Candidate

class APITests(APITestCase):

    def setUp(self):
        # self.company = Company.objects.create(company_name="Test Company")
        self.job = Job.objects.create(
            # company=self.company,
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

    # def test_company_list(self):
    #     url = reverse('company-list')
    #     response = self.client.get(url, format='json')
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_job_list(self):
        url = reverse('job-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_candidate_list(self):
        url = reverse('candidate-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
