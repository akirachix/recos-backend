from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from job.models import  Job
from .models import Candidate

class CandidateTests(APITestCase):

    def setUp(self):
        self.job = Job.objects.create(
            job_title="Software Engineer",
            job_description="Develop software",
            generated_job_summary="Develop software",
            expired_at="2099-12-31T23:59:59Z",
        )

    def test_create_candidate(self):
        url = reverse("candidate-list")
        data = {
            "name": "Alice",
            "email": "alice@example.com",
            "job": self.job.job_id,
            "generated_skill_summary": "Python, Django",
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Candidate.objects.count(), 1)
        self.assertEqual(Candidate.objects.get().name, "Alice")

    def test_list_candidates(self):
        Candidate.objects.create(
            name="Bob",
            email="bob@example.com",
            job=self.job,
            generated_skill_summary="Python",
        )
        url = reverse("candidate-list")
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)
