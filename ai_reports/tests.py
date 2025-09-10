from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import AIReport

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