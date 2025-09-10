
from django.shortcuts import render

from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.authtoken.models import Token
from interviewConversation.models import InterviewConversation
from job.models import Job
from candidate.models import Candidate
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.utils.encoding import force_bytes, force_str
from users.models import Recruiter, OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
import random
from django.utils import timezone
from datetime import timedelta
from ai_reports.models import AIReport
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from interviewConversation.models import InterviewConversation
from job.models import Job
from candidate.models import Candidate
from interview.models import Interview
from .serializers import (
    InterviewConversationSerializer, 
    JobSerializer, 
    CandidateSerializer, 
    InterviewSerializer,
    RecruiterSerializer, 
    OdooCredentialsSerializer, 
    CompanySerializer,
    AIReportSerializer, 
    AIReportCreateSerializer
)
from interview.utils import create_google_calendar_event

class InterviewConversationViewSet(viewsets.ModelViewSet):
    queryset = InterviewConversation.objects.all()
    serializer_class = InterviewConversationSerializer

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

class RecruiterRegistrationView(generics.CreateAPIView):
    queryset = Recruiter.objects.all()
    serializer_class = RecruiterSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        user = Recruiter.objects.get(email=serializer.data['email'])
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': serializer.data,
            'token': token.key
        }, status=status.HTTP_201_CREATED, headers=headers)
    

class RecruiterListView(generics.ListAPIView):
    queryset = Recruiter.objects.all()
    serializer_class = RecruiterSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Recruiter.objects.all()
        return Recruiter.objects.filter(id=self.request.user.id)

    
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    email = request.data.get('email') 
    password = request.data.get('password')
    
    if email and password:
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'message': 'Login successful',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            })
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
def verify_odoo_account(request):
    try:
        db_url = request.data.get('db_url')
        db_name = request.data.get('db_name')
        email = request.data.get('email')
        api_key = request.data.get('api_key')
        
        if not all([db_url, db_name, email, api_key]):
            return Response({'error': 'All fields (db_url, db_name, email, api_key) are required'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        odoo_service = OdooService(db_url, db_name, email, api_key)
        if odoo_service.authenticate():
            return Response({'valid': True, 'message': 'Odoo account verified successfully'})
        else:
            return Response({'valid': False, 'error': 'Invalid Odoo credentials'}, 
                            status=status.HTTP_401_UNAUTHORIZED)
    
    except requests.exceptions.ConnectionError:
        return Response({'valid': False, 'error': 'Could not connect to Odoo instance'}, 
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    except Exception as e:
        return Response({'valid': False, 'error': f'An error occurred: {str(e)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def logout_view(request):
    if request.user.is_authenticated:
        try:
            request.user.auth_token.delete()
        except:
            pass
        logout(request)
        return Response({'message': 'Logout successful'})
    return Response({'error': 'You are not logged in'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_odoo_credentials(request):
    if not request.user.has_perm('users.ass_odoocredentials'):
        return Response({'error':'You do not have permission to add Odoo Credentials'}, status=status.HTTP_403_FORBIDDEN)
    db_url = request.data.get('db_url')
    db_name = request.data.get('db_name')
    email = request.data.get('email')
    api_key = request.data.get('api_key')
    
    if not all([db_url, db_name, email, api_key]):
        return Response({'error': 'All fields (db_url, db_name, email, api_key) are required'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    odoo_service = OdooService(db_url, db_name, email, api_key)
    if not odoo_service.authenticate():
        return Response({'error': 'Invalid Odoo credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        user_info = odoo_service.get_user_info()
        if not user_info:
            return Response({'error': 'Failed to retrieve user info from Odoo'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        odoo_user_id = user_info[0]['id']
    except Exception as e:
        return Response({'error': f'Failed to retrieve user info: {str(e)}'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    credentials, created = OdooCredentials.objects.update_or_create(
        recruiter=request.user,
        odoo_user_id=odoo_user_id,
        defaults={
            'api_key': api_key, 
            'email_address': email,
            'db_name': db_name,
            'db_url': db_url,
        }
    )
    
    try:
        companies = odoo_service.get_companies()
        for company in companies:
            Company.objects.get_or_create(
            odoo_company_id=company['id'],
            recruiter=request.user,
            defaults={'company_name':company['name'],'created_at': timezone.now(), 'updated_at': timezone.now()}
    )
    except Exception as e:
        return Response({'error': f'Failed to retrieve companies: {str(e)}'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    serializer = OdooCredentialsSerializer(credentials)
    return Response({
        'message': 'Odoo credentials added successfully',
        'credentials': serializer.data,
        'companies': companies
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@api_view(['GET'])
def get_odoo_credentials(request):
    credentials = OdooCredentials.objects.filter(recruiter=request.user)
    serializer = OdooCredentialsSerializer(credentials, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_companies(request):
    companies = Company.objects.filter(recruiter=request.user)
    serializer = CompanySerializer(companies, many=True)
    return Response(serializer.data)
    
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'message': 'Welcome to Recos Platform API',
        'endpoints': {
            'register': reverse('register', request=request, format=format),
            'login': reverse('login', request=request, format=format),
            'logout': reverse('logout', request=request, format=format),
            'forgot-password':reverse('forgot_password', request=request, format=format),
            'verify-odoo': reverse('verify_odoo_account', request=request, format=format),
            'odoo-credentials': reverse('add_odoo_credentials', request=request, format=format),
            'odoo-credentials-list': reverse('get_odoo_credentials', request=request, format=format),
            'companies': reverse('get_companies', request=request, format=format),
            'users': reverse('recruiter_list', request=request, format=format),  # Add this line
        }
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def forgot_password(request):
    email = request.data.get('email')
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Recruiter.objects.get(email=email)
    except Recruiter.DoesNotExist:
        return Response({'message': 'Password reset code sent if email exists in our system'}, 
                        status=status.HTTP_200_OK)
    
    verification_code = ''.join(random.choices('0123456789', k=6))
    
    user.verification_code = verification_code
    user.verification_code_expires = timezone.now() + timedelta(minutes=15)
    user.save()
    
    subject = 'Password Reset Verification Code'
    message = render_to_string('api/password_reset_email.html', {
        'user': user,
        'code': verification_code,
        'site_name': getattr(settings, 'SITE_NAME', 'Your Site Name'),
        'expiration_minutes': 15,
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=message,
    )
    
    return Response({'message': 'Password reset code sent.'}, 
                    status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password(request):
    email = request.data.get('email')
    code = request.data.get('code')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    if not email or not code or not new_password or not confirm_password:
        return Response({
            'error': 'Email, code, new_password, and confirm_password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if new_password != confirm_password:
        return Response({
            'error': 'Passwords do not match'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Recruiter.objects.get(email=email)
    except Recruiter.DoesNotExist:
        return Response({
            'error': 'Invalid email address'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not user.is_verification_code_valid(code):
        return Response({
            'error': 'Invalid or expired verification code'
        }, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(new_password)
    user.verification_code = None 
    user.verification_code_expires = None
    user.save()
    
    return Response({
        'message': 'Password has been reset successfully'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_reset_code(request):
    email = request.data.get('email')
    code = request.data.get('code')
    
    if not email or not code:
        return Response({
            'error': 'Email and code are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = Recruiter.objects.get(email=email)
    except Recruiter.DoesNotExist:
        return Response({
            'valid': False,
            'error': 'Invalid email address'
        }, status=status.HTTP_400_BAD_REQUEST)
    if user.is_verification_code_valid(code):
        return Response({
            'valid': True
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'valid': False,
            'error': 'Invalid or expired verification code'
        }, status=status.HTTP_400_BAD_REQUEST)
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

class InterviewViewSet(viewsets.ModelViewSet):
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = serializer.save()

   
        event_id, hangout_link = create_google_calendar_event(interview)
        interview.google_event_id = event_id
        interview.interview_link = hangout_link
        interview.save()
        output_serializer = self.get_serializer(interview)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
