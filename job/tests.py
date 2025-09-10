
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Job

class JobTests(APITestCase):

    def test_create_job(self):
        url = reverse("job-list") 
        data = {
            "job_title": "Software Engineer",
            "job_description": "Develop software",
            "generated_job_summary": "Develop software",
            "expired_at": "2099-12-31T23:59:59Z",
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Job.objects.count(), 1)
        self.assertEqual(Job.objects.get().job_title, "Software Engineer")

    def test_list_jobs(self):
        Job.objects.create(job_title="Test 1", job_description="desc", generated_job_summary="sum", expired_at="2099-12-31T23:59:59Z")
        url = reverse("job-list")
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

