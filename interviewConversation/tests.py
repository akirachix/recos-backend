from django.test import TestCase


from .models import InterviewConversation
from django.utils import timezone

class InterviewConversationModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.conversation = InterviewConversation.objects.create(
            question_text="What is your name?",
            expected_answer="My name is Ciggie",
            candidate_answer="My name is Ciggie",
            transcript_time=timezone.now()
        )

    def test_fields_content(self):
      conv = InterviewConversation.objects.get(conversation_id=self.conversation.conversation_id)
      self.assertEqual(conv.question_text, "What is your name?")
      self.assertEqual(conv.expected_answer, "My name is Ciggie")
      self.assertEqual(conv.candidate_answer, "My name is Ciggie")
      self.assertIsNotNone(conv.transcript_time)

    def test_str_method(self):
        conv = InterviewConversation.objects.get(conversation_id=self.conversation.conversation_id)
        expected_str = f"Conversation {conv.conversation_id}"
        self.assertEqual(str(conv), expected_str)
