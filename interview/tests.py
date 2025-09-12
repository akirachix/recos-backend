from django.test import SimpleTestCase

class MockCandidate:
    def __init__(self, name):
        self.name = name

class MockRecruiter:
    def __init__(self, name):
        self.name = name

class MockInterview:
    def __init__(self, candidate, recruiter, title, status):
        self.candidate = candidate
        self.recruiter = recruiter
        self.title = title
        self.status = status

    def get_status_display(self):
        mapping = {
            "scheduled": "Scheduled",
            "in_progress": "In Progress",
            "completed": "Completed",
            "canceled": "Canceled"
        }
        return mapping.get(self.status, self.status)

    def __str__(self):
        return f"{self.candidate.name} - {self.title} - {self.get_status_display()}"

class InterviewModelLogicTest(SimpleTestCase):
    def test_str_method_logic(self):
        candidate = MockCandidate("Alice Johnson")
        recruiter = MockRecruiter("Bob Smith")
        interview = MockInterview(
            candidate=candidate,
            recruiter=recruiter,
            title="Backend Developer Interview",
            status="scheduled"
        )
        expected = "Alice Johnson - Backend Developer Interview - Scheduled"
        self.assertEqual(str(interview), expected)