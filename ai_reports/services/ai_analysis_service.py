# ai_reports/services/ai_analysis_service.py
import json
import google.genai as genai
from google.genai import types
from django.conf import settings
from candidate.models import CandidateAttachment
from job.models import Job
from interviewConversation.models import InterviewConversation
from ai_reports.utils import extract_text_from_file_object


def get_genai_client():
    """Initialize and return a Google GenAI client"""
    try:
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            return None
            
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Error initializing GenAI client: {e}")
        return None


def parse_gemini_response(response_text):
    """Parse Gemini response and extract JSON"""
    try:
        cleaned_text = response_text.strip()
        if '```json' in cleaned_text:
            cleaned_text = cleaned_text.split('```json')[1].split('```')[0].strip()
        elif '```' in cleaned_text:
            cleaned_text = cleaned_text.split('```')[1].split('```')[0].strip()
        
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return {"raw_response": response_text}


class AIAnalysisService:
    def __init__(self):
        self.client = get_genai_client()
        
    def extract_text_from_attachment(self, attachment):
        """Extract text from CV attachment (PDF or DOCX)"""
        if not attachment.file:
            return ""
            
        return extract_text_from_file_object(attachment.file)
    
    def get_candidate_cv_text(self, candidate):
        """Get the text content of the candidate's CV"""
        cv_attachments = candidate.attachments.filter(file_type__icontains='pdf') | \
                         candidate.attachments.filter(file_type__icontains='document')
        
        if not cv_attachments.exists():
            return ""
            
        # Use the most recent CV attachment
        latest_cv = cv_attachments.latest('created_at')
        return self.extract_text_from_attachment(latest_cv)
    
    def calculate_skill_match_score(self, candidate, job):
        """Calculate skill match score between candidate CV and job description"""
        cv_text = self.get_candidate_cv_text(candidate)
        job_description = job.job_description
        
        if not cv_text or not job_description:
            return {"overall_score": 0.0, "skills_breakdown": {}}
            
        if not self.client:
            return {"overall_score": 0.0, "skills_breakdown": {}}
            
        prompt = f"""
        You are an expert HR analyst. Analyze the match between the following candidate CV and job description.
        
        TASK:
        1. Identify key skills required for the job from the job description
        2. Extract relevant skills and experience from the candidate's CV
        3. Calculate a match score from 0 to 100 indicating how well the candidate's skills match the job requirements
        4. Provide a breakdown of key skills and how well the candidate matches each one
        
        Job Description:
        {job_description}
        
        Candidate CV:
        {cv_text}
        
        Return your response in the following JSON format:
        {{
            "overall_score": <score between 0-100>,
            "skills_breakdown": {{
                "skill1": <score between 0-100>,
                "skill2": <score between 0-100>,
                ...
            }}
        }}
        """
        
        try:
            config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
                response_mime_type="application/json",
            )
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config,
            )
            
            result = parse_gemini_response(response.text)
            return result
        except Exception as e:
            print(f"Error calculating skill match score: {e}")
            return {"overall_score": 0.0, "skills_breakdown": {}}
    
    def generate_tailored_questions(self, candidate, job, num_questions=5):
        """Generate tailored interview questions based on candidate CV and job description"""
        cv_text = self.get_candidate_cv_text(candidate)
        job_description = job.job_description
        
        if not cv_text or not job_description:
            return []
            
        if not self.client:
            return []
            
        prompt = f"""
        You are an expert interviewer. Based on the following job description and candidate CV, generate {num_questions} tailored interview questions.
        
        TASK:
        1. Analyze the key requirements of the job from the job description
        2. Review the candidate's experience and skills from their CV
        3. Create questions that:
           - Test the candidate's knowledge of key skills required for the job
           - Explore any gaps between the candidate's experience and job requirements
           - Focus on areas where the candidate has relevant experience
           - Are open-ended to encourage detailed responses
        
        Job Description:
        {job_description}
        
        Candidate CV:
        {cv_text}
        
        Return your response as a JSON array of questions, each with a question_text and expected_answer:
        {{
            "questions": [
                {{
                    "question_text": "Question 1",
                    "expected_answer": "Expected answer for question 1"
                }},
                ...
            ]
        }}
        """
        
        try:
            config = types.GenerateContentConfig(
                temperature=0.3,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
                response_mime_type="application/json",
            )
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config,
            )
            
            result = parse_gemini_response(response.text)
            return result.get("questions", [])
        except Exception as e:
            print(f"Error generating tailored questions: {e}")
            return []
    
    def analyze_interview_performance(self, interview_id):
        """Analyze candidate performance from interview conversation"""
        conversations = InterviewConversation.objects.filter(interview_id=interview_id)
        
        if not conversations.exists():
            return {
                "final_match_score": 0.0,
                "strengths": "",
                "weaknesses": "",
                "overall_recommendation": "",
                "performance_analysis": {}
            }
            
        if not self.client:
            return {
                "final_match_score": 0.0,
                "strengths": "",
                "weaknesses": "",
                "overall_recommendation": "",
                "performance_analysis": {}
            }
            
        # Get the interview to access the associated job and candidate
        from interview.models import Interview
        interview = Interview.objects.get(interview_id=interview_id)
        candidate = interview.candidate
        job = candidate.job
        
        # Format conversations for analysis
        conversation_text = ""
        for conv in conversations:
            conversation_text += f"Q: {conv.question_text}\n"
            if conv.expected_answer:
                conversation_text += f"Expected: {conv.expected_answer}\n"
            conversation_text += f"A: {conv.candidate_answer}\n\n"
        
        prompt = f"""
        You are an expert hiring manager. Analyze the following interview conversation and provide a comprehensive assessment of the candidate's performance.
        
        CONTEXT:
        - Job Title: {job.job_title}
        - Job Description: {job.job_description}
        - Candidate Name: {candidate.name}
        
        TASK:
        1. Evaluate how well the candidate answered the questions
        2. Assess their technical knowledge and problem-solving skills
        3. Identify strengths demonstrated during the interview
        4. Identify weaknesses or areas for improvement
        5. Provide a final match score (0-100) based on their interview performance
        6. Give a recommendation for hiring decision
        
        Interview Conversation:
        {conversation_text}
        
        Provide your assessment in the following JSON format:
        {{
            "final_match_score": <score between 0-100>,
            "strengths": "<detailed description of candidate's strengths>",
            "weaknesses": "<detailed description of candidate's weaknesses>",
            "overall_recommendation": "<detailed recommendation for hiring decision>",
            "performance_analysis": {{
                "communication_skills": "<assessment>",
                "technical_knowledge": "<assessment>",
                "problem_solving": "<assessment>",
                "cultural_fit": "<assessment>"
            }}
        }}
        """
        
        try:
            config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
                response_mime_type="application/json",
            )
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config,
            )
            
            result = parse_gemini_response(response.text)
            return result
        except Exception as e:
            print(f"Error analyzing interview performance: {e}")
            return {
                "final_match_score": 0.0,
                "strengths": "",
                "weaknesses": "",
                "overall_recommendation": "",
                "performance_analysis": {}
            }
    
    def generate_complete_ai_report(self, interview_id):
        """Generate a complete AI report for an interview"""
        from interview.models import Interview
        from ai_reports.models import AIReport
        
        try:
            interview = Interview.objects.get(interview_id=interview_id)
            candidate = interview.candidate
            job = candidate.job  # This ensures we're using the correct job associated with the candidate
            
            # Calculate skill match score
            skill_match_result = self.calculate_skill_match_score(candidate, job)
            skill_match_score = skill_match_result.get("overall_score", 0.0)
            skills_breakdown = skill_match_result.get("skills_breakdown", {})
            
            # Analyze interview performance
            performance_result = self.analyze_interview_performance(interview_id)
            final_match_score = performance_result.get("final_match_score", 0.0)
            strengths = performance_result.get("strengths", "")
            weaknesses = performance_result.get("weaknesses", "")
            overall_recommendation = performance_result.get("overall_recommendation", "")
            performance_analysis = performance_result.get("performance_analysis", {})
            
            # Generate tailored questions
            tailored_questions = self.generate_tailored_questions(candidate, job)
            
            # Create or update AI report
            ai_report, created = AIReport.objects.update_or_create(
                conversation_id=InterviewConversation.objects.filter(interview_id=interview_id).first(),
                defaults={
                    "skill_match_score": skill_match_score,
                    "final_match_score": final_match_score,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "overall_recommendation": overall_recommendation,
                    "skills_breakdown": skills_breakdown,
                    "performance_analysis": performance_analysis,
                    "tailored_questions": tailored_questions
                }
            )
            
            return ai_report
        except Exception as e:
            print(f"Error generating complete AI report: {e}")
            return None