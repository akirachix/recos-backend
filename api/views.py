from django.shortcuts import render

from interviewConversation.models import InterviewConversation
from job.models import Job
from candidate.models import Candidate
from .serializers import InterviewConversationSerializer, JobSerializer, CandidateSerializer, AIReportSerializer, AIReportCreateSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ai_reports.models import AIReport
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

class InterviewConversationViewSet(viewsets.ModelViewSet):
    queryset = InterviewConversation.objects.all()
    serializer_class = InterviewConversationSerializer

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer


def draw_wrapped_text(p, text, x, y, max_width, font_name="Helvetica", font_size=12, line_height=16, page_margin=100, page_height=letter[1]):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split()
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if stringWidth(test_line, font_name, font_size) <= max_width:
            line = test_line
        else:
            p.drawString(x, y, line)
            y -= line_height
            if y < page_margin:
                p.showPage()
                y = page_height - page_margin
                p.setFont(font_name, font_size)
            line = word
    if line:
        p.drawString(x, y, line)
        y -= line_height
    return y

class AIReportViewSet(viewsets.ModelViewSet):
    queryset = AIReport.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update', 'generate_report']:
            return AIReportCreateSerializer
        return AIReportSerializer

    @action(detail=False, methods=['get'], url_path=r'by-conversation/(?P<conversation_id>\d+)')
    def by_conversation(self, request, conversation_id=None):
        ai_reports = AIReport.objects.filter(conversation_id=conversation_id)
        serializer = AIReportSerializer(ai_reports, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        conversation_id = request.data.get('conversation_id')
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if AIReport.objects.filter(conversation_id=conversation_id).exists():
            return Response(
                {'error': 'AI report already exists for this conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        
        ai_report_data = {
            "conversation_id": conversation_id,
            "skill_match_score": 78.25,
            "final_match_score": 81.50,
            "strengths": (
                "The candidate demonstrated exceptional knowledge in Python and Django frameworks, articulating complex concepts with clarity and confidence. Throughout the discussion, they provided in-depth explanations of asynchronous programming, RESTful API design, and database optimization strategies. In addition, the candidate showcased a strong understanding of version control best practices and CI/CD pipelines, referencing real-world scenarios where these skills were crucial to project success. Their communication skills were evident as they broke down difficult problems into manageable components, offered insightful questions, and maintained a collaborative tone. Furthermore, the candidate's experience with cloud deployment and Docker containers was apparent, as they detailed step-by-step processes, potential pitfalls, and best practices for maintaining reliable production environments."
            ),
            "weaknesses": (
                "While the candidate possesses a solid foundation in backend technologies, their exposure to frontend frameworks such as React and Angular appears limited. During the interview, the candidate struggled to articulate modern frontend design patterns and was unable to provide concrete examples of implementing state management or optimizing component performance. Additionally, the candidate showed some hesitation when asked about advanced database indexing techniques and had difficulty describing scenarios for using NoSQL solutions effectively. Time management during problem-solving was also a concern, as the candidate occasionally delved too deeply into specifics, resulting in incomplete answers for some questions."
            ),
            "overall_recommendation": (
                "Based on the assessment, the candidate is recommended for advancement to the next stage, particularly for roles emphasizing backend development and cloud infrastructure. Their expertise in Python, Django, and DevOps practices would be a valuable asset to any engineering team. However, it is recommended that the candidate undertake additional training or mentorship in frontend technologies and database performance tuning to ensure well-roundedness in future projects. Providing opportunities for cross-functional collaboration and exposure to full-stack challenges would likely accelerate the candidate's growth and address current skill gaps. Overall, with focused professional development, the candidate is likely to become a high-impact contributor."
            ),
            "skills_breakdown": {
                "Python": 90,
                "Django": 85,
                "REST APIs": 80,
                "CI/CD": 75,
                "Docker": 70,
                "Cloud": 68,
                "Frontend": 40,
                "Database Optimization": 55
            },
            "initial_analysis": {
                "Python": 45,
                "Problem Solving": 38,
                "Django": 30,
                "Cloud": 20
            },
            "performance_analysis": {
                "Attention to Detail": "High",
                "Technical Skills": "High",
                "Problem Solving": "Medium",
                "AI Confidence": "High"
            }
        }

        serializer = AIReportCreateSerializer(data=ai_report_data)
        if serializer.is_valid():
            serializer.save()
            read_serializer = AIReportSerializer(serializer.instance)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_score(self, request, pk=None):
        ai_report = self.get_object()
        new_score = request.data.get('skill_match_score')

        if new_score is None:
            return Response(
                {'error': 'skill_match_score is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_score = float(new_score)
            if not (0 <= new_score <= 100):
                raise ValueError("Score must be between 0 and 100")
        except (ValueError, TypeError):
            return Response(
                {'error': 'skill_match_score must be a valid number between 0 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ai_report.skill_match_score = new_score
        ai_report.save(update_fields=['skill_match_score'])  

        serializer = AIReportSerializer(ai_report)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download_report(self, request, pk=None):
        ai_report = self.get_object()
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        y = height - 40
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, y, "Candidate  Report")
        y -= 30

        p.setFont("Helvetica", 12)
        #link to candidate name applied
        p.drawString(50, y, f"Candidate Name: Johnny Gait")
        y -= 20
        #link to job possition applied
        p.drawString(50, y, f"Position Applied: Backend Developer")
        y -= 20
        p.drawString(50, y, f"Skill Match Score: {ai_report.skill_match_score}")
        y -= 20
        p.drawString(50, y, f"Final Match Score: {ai_report.final_match_score}")
        y -= 20

        max_width = width - 80
        y -= 10
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Strengths:")
        y -= 16
        p.setFont("Helvetica", 12)
        y = draw_wrapped_text(p, ai_report.strengths or "-", 50, y, max_width)

        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Weaknesses:")
        y -= 16
        p.setFont("Helvetica", 12)
        y = draw_wrapped_text(p, ai_report.weaknesses or "-", 50, y, max_width)

        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Overall Recommendation:")
        y -= 16
        p.setFont("Helvetica", 12)
        y = draw_wrapped_text(p, ai_report.overall_recommendation or "-", 50, y, max_width)
        y -= 10

        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Skills Breakdown:")
        y -= 16
        p.setFont("Helvetica", 12)
        skills = ai_report.skills_breakdown or {}
        for skill, percent in skills.items():
            p.drawString(60, y, f"{skill}: {percent}%")
            y -= 16
            if y < 60:
                p.showPage()
                y = height - 40
                p.setFont("Helvetica", 12)

        y -= 10
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Initial Analysis:")
        y -= 16
        p.setFont("Helvetica", 12)
        initial = ai_report.initial_analysis or {}
        for k, v in initial.items():
            p.drawString(60, y, f"{k}: {v}%")
            y -= 16
            if y < 60:
                p.showPage()
                y = height - 40
                p.setFont("Helvetica", 12)

        y -= 10
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Interview Performance Analysis:")
        y -= 16
        p.setFont("Helvetica", 12)
        perf = ai_report.performance_analysis or {}
        for k, v in perf.items():
            p.drawString(60, y, f"{k}: {v}")
            y -= 16
            if y < 60:
                p.showPage()
                y = height - 40
                p.setFont("Helvetica", 12)

        p.showPage()
        p.save()

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ai_report_{ai_report.report_id}.pdf"'
        return response