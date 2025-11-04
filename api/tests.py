from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from users.models import Recruiter
from companies.models import Company
from job.models import Job
from candidate.models import Candidate
from interview.models import Interview

class JobSummaryTests(APITestCase):

    def setUp(self):
        self.recruiter = Recruiter.objects.create_user(email='test@example.com', password='password', first_name='test', last_name='user')
        self.company = Company.objects.create(company_name='Test Company', recruiter=self.recruiter)
        self.job = Job.objects.create(job_title='Test Job', company=self.company, posted_at='2025-10-27T10:00:00Z')
        self.candidate = Candidate.objects.create(job=self.job, name='Test Candidate', email='candidate@example.com')
        self.interview = Interview.objects.create(
            candidate=self.candidate,
            recruiter=self.recruiter,
            title='Test Interview',
            scheduled_at='2025-11-10T10:00:00Z',
            status='scheduled'
        )
        self.client.force_authenticate(user=self.recruiter)

    def test_job_summary_endpoint(self):
        url = reverse('job-summary')
        response = self.client.get(url, {'company_id': self.company.company_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        summary = response.data[0]
        self.assertEqual(summary['job_id'], self.job.job_id)
        self.assertEqual(summary['total_candidates'], 1)
        self.assertEqual(summary['scheduled_interviews'], 1)
        self.assertEqual(summary['interviews_done'], 0)
