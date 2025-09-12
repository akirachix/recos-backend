from django.test import SimpleTestCase
from datetime import datetime

class MockInterview:
    def __init__(self, id=1):
        self.id = id

class MockInterviewConversation:
    def __init__(self, conversation_id, interview, question_text, expected_answer, candidate_answer, transcript_time):
        self.conversation_id = conversation_id
        self.interview = interview
        self.question_text = question_text
        self.expected_answer = expected_answer
        self.candidate_answer = candidate_answer
        self.transcript_time = transcript_time

    def __str__(self):
        return f"Conversation {self.conversation_id}"

class InterviewConversationModelLogicTest(SimpleTestCase):
    def setUp(self):
        interview = MockInterview(id=1)
        self.conversation = MockInterviewConversation(
            conversation_id=1,
            interview=interview,
            question_text="What is your name?",
            expected_answer="My name is Ciggie",
            candidate_answer="My name is Ciggie",
            transcript_time=datetime.now()
        )

    def test_fields_content(self):
        conv = self.conversation
        self.assertEqual(conv.question_text, "What is your name?")
        self.assertEqual(conv.expected_answer, "My name is Ciggie")
        self.assertEqual(conv.candidate_answer, "My name is Ciggie")
        self.assertIsNotNone(conv.transcript_time)

    def test_str_method(self):
        conv = self.conversation
        expected_str = f"Conversation {conv.conversation_id}"
        self.assertEqual(str(conv), expected_str)