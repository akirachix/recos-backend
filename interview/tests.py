from django.test import TestCase
from django.utils import timezone
from .models import Interview

class InterviewModelTest(TestCase):
    def test_create_interview(self):
        scheduled_time = timezone.now()
        interview = Interview.objects.create(
            scheduled_at=scheduled_time,
            status='Scheduled',
        )
        self.assertIsInstance(interview, Interview)
        self.assertEqual(interview.status, 'Scheduled')
        self.assertEqual(interview.scheduled_at, scheduled_time)
        self.assertIsNone(interview.interview_link)
        self.assertIsNone(interview.google_event_id)
        self.assertIsNotNone(interview.created_at)
        self.assertIsNotNone(interview.updated_at)
        self.assertEqual(str(interview), f"Interview: {interview.pk} ({interview.status})")