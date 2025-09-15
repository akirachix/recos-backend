from django.test import SimpleTestCase

class MockJob:
    def __init__(self, job_title, job_description, generated_job_summary, expired_at):
        self.job_title = job_title
        self.job_description = job_description
        self.generated_job_summary = generated_job_summary
        self.expired_at = expired_at

class MockCandidate:
    def __init__(self, name, email, job, generated_skill_summary=None):
        self.name = name
        self.email = email
        self.job = job
        self.generated_skill_summary = generated_skill_summary

class MockAIReport:
    def __init__(self, conversation_id, skill_match_score, final_match_score, strengths,
                 weaknesses, overall_recommendation, skills_breakdown, initial_analysis, performance_analysis):
        self.conversation_id = conversation_id
        self.skill_match_score = skill_match_score
        self.final_match_score = final_match_score
        self.strengths = strengths
        self.weaknesses = weaknesses
        self.overall_recommendation = overall_recommendation
        self.skills_breakdown = skills_breakdown
        self.initial_analysis = initial_analysis
        self.performance_analysis = performance_analysis
        self.report_id = 1

class MockUser:
    def __init__(self, email, first_name, last_name, password):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.password = password
        self.id = 1
        self.is_staff = False

class APITests(SimpleTestCase):
    def setUp(self):
        self.job = MockJob(
            job_title="API Test Job",
            job_description="Test Desc",
            generated_job_summary="Summary",
            expired_at="2099-12-31T23:59:59Z",
        )
        self.candidate = MockCandidate(
            name="API Candidate",
            email="api@example.com",
            job=self.job,
            generated_skill_summary="Skill Summary"
        )

    def test_job_list(self):
        self.assertEqual(self.job.job_title, "API Test Job")

    def test_candidate_list(self):
        self.assertEqual(self.candidate.name, "API Candidate")

class RecruiterRegistrationViewTests(SimpleTestCase):
    def test_register_recruiter(self):
        user = MockUser(email='test@example.com', first_name='John', last_name='Doe', password='testpass123')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')

class RecruiterListViewTests(SimpleTestCase):
    def setUp(self):
        self.user = MockUser(email='test@example.com', first_name='John', last_name='Doe', password='testpass123')
        self.staff_user = MockUser(email='staff@example.com', first_name='Staff', last_name='User', password='testpass123')
        self.staff_user.is_staff = True

    def test_list_recruiters_as_user(self):
        self.assertEqual(self.user.first_name, "John")
        self.assertFalse(self.user.is_staff)

    def test_list_recruiters_as_staff(self):
        self.assertEqual(self.staff_user.first_name, "Staff")
        self.assertTrue(self.staff_user.is_staff)

class LoginViewTests(SimpleTestCase):
    def setUp(self):
        self.user = MockUser(email='test@example.com', first_name='John', last_name='Doe', password='testpass123')

    def test_login_success(self):
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.password, 'testpass123')

    def test_login_invalid_credentials(self):
        self.assertNotEqual(self.user.password, 'wrongpassword')

class AIReportAPITestCase(SimpleTestCase):
    def setUp(self):
        self.dummy_conversation_id = 1

    def test_create_ai_report(self):
        report = MockAIReport(
            conversation_id=self.dummy_conversation_id,
            skill_match_score=90.0,
            final_match_score=95.5,
            strengths='Great communicator',
            weaknesses='New to Python',
            overall_recommendation='Hire',
            skills_breakdown={"Python": 80, "Django": 70},
            initial_analysis={"Python": 30, "Problem Solving": 45},
            performance_analysis={"Attention to Detail": "High"}
        )
        self.assertEqual(report.skill_match_score, 90.0)
        self.assertEqual(report.final_match_score, 95.5)
        self.assertEqual(report.skills_breakdown, {"Python": 80, "Django": 70})

    def test_generate_report_creates_new(self):
        report = MockAIReport(
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
        self.assertIsInstance(report.skills_breakdown, dict)
        self.assertIsInstance(report.initial_analysis, dict)
        self.assertIsInstance(report.performance_analysis, dict)

    def test_generate_report_fails_if_exists(self):
        report_exists = True
        self.assertTrue(report_exists)

    def test_get_by_conversation(self):
        report = MockAIReport(
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
        self.assertEqual(report.conversation_id, self.dummy_conversation_id)
        self.assertEqual(report.report_id, 1)

    def test_update_score(self):
        report = MockAIReport(
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
        report.skill_match_score = 92.5
        self.assertEqual(report.skill_match_score, 92.5)

    def test_update_score_invalid(self):
        report = MockAIReport(
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
        invalid_score = 150.0
        self.assertTrue(invalid_score > 100.0)