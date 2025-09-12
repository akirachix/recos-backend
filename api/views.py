from django.shortcuts import render
from django.contrib.auth.models import Permission
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
from companies.services.company_sync_service import CompanySyncService


class InterviewConversationViewSet(viewsets.ModelViewSet):
    queryset = InterviewConversation.objects.all()
    serializer_class = InterviewConversationSerializer

class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        recruiter = self.request.user
        print(f"Fetching jobs for recruiter: {recruiter.email}")
        
        companies = Company.objects.filter(recruiter=recruiter)
        print(f"Found {companies.count()} companies for this recruiter")
        
        queryset = Job.objects.filter(company__in=companies)
        print(f"Found {queryset.count()} jobs for these companies")
        
        company_id = self.request.query_params.get('company_id', None)
        if company_id is not None:
            print(f"Filtering by company_id: {company_id}")
            queryset = queryset.filter(company_id=company_id)
            print(f"After filtering, found {queryset.count()} jobs")
        
        return queryset
    
class CandidateViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):   
        recruiter = self.request.user
        companies = Company.objects.filter(recruiter=recruiter)
        jobs = Job.objects.filter(company__in=companies)
        queryset = Candidate.objects.filter(job__in=jobs)
        
        job_id = self.request.query_params.get('job_id', None)
        if job_id is not None:
            queryset = queryset.filter(job_id=job_id)
            
        return queryset
    
    def perform_create(self, serializer):
        job_id = self.request.data.get('job_id')
        if job_id:
            try:
                job = Job.objects.get(job_id=job_id, company__recruiter=self.request.user)
                serializer.save(
                    job=job,
                    company=job.company  
                )
            except Job.DoesNotExist:
                raise serializers.ValidationError("Job not found or doesn't belong to you")
        else:
            raise serializers.ValidationError("job_id is required")

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
        try:
            perm = Permission.objects.get(name='add_odoocredentials')
            user.user_permissions.add(perm)
            user.save()
        except Permission.DoesNotExist:
            pass
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

@api_view(['GET'])
def get_odoo_credentials(request):
    credentials = OdooCredentials.objects.filter(recruiter=request.user)
    serializer = OdooCredentialsSerializer(credentials, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_jobs_by_company(request, company_id):
    try:
        company = Company.objects.get(company_id=company_id, recruiter=request.user)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found or access denied'}, status=status.HTTP_404_NOT_FOUND)
    
    jobs = Job.objects.filter(company=company)
    serializer = JobSerializer(jobs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_candidates_by_job(request, job_id):
    try:
        job = Job.objects.get(job_id=job_id, recruiter=request.user)
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    candidates = Candidate.objects.filter(job=job, recruiter=request.user)
    serializer = CandidateSerializer(candidates, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_jobs_for_company(request, company_id):
    try:
        try:
            company = Company.objects.get(company_id=company_id, recruiter=request.user)
        except Company.MultipleObjectsReturned:
            company = Company.objects.filter(company_id=company_id, recruiter=request.user).first()
            if not company:
                return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        from job.services.job_sync_service import JobSyncService
        synced_jobs = JobSyncService.sync_jobs_for_company(company)
        serializer = JobSerializer(synced_jobs, many=True)
        return Response({
            'message': f'Successfully synced {len(synced_jobs)} jobs',
            'jobs': serializer.data
        })
    except Exception as e:
        return Response({'error': f'Failed to sync jobs: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_candidates_for_job(request, job_id):
    try:
        job = Job.objects.get(job_id=job_id, recruiter=request.user)
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    try:
        synced_candidates = CandidateSyncService.sync_candidates_for_job(job)
        serializer = CandidateSerializer(synced_candidates, many=True)
        return Response({
            'message': f'Successfully synced {len(synced_candidates)} candidates',
            'candidates': serializer.data
        })
    except Exception as e:
        return Response({'error': f'Failed to sync candidates: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_all_data(request):
    try:
        synced_companies = CompanySyncService.sync_recruiter_companies(request.user, sync_jobs=True)
        all_candidates = []
        for company in synced_companies:
            for job in company.jobs.all():
                try:
                    synced_candidates = CandidateSyncService.sync_candidates_for_job(job)
                    all_candidates.extend(synced_candidates)
                except Exception as e:
                    print(f"Error syncing candidates for job {job.job_title}: {str(e)}")
        
        companies_data = CompanySerializer(synced_companies, many=True).data
        candidates_data = CandidateSerializer(all_candidates, many=True).data
        
        return Response({
            'message': f'Successfully synced {len(synced_companies)} companies and {len(all_candidates)} candidates',
            'companies': companies_data,
            'candidates': candidates_data
        })
    except Exception as e:
        return Response({'error': f'Failed to sync data: {str(e)}'}, 
                        status=status.HTTP_400_BAD_REQUEST)


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
    message = (
        f"Hello {user.first_name},\n\n"
        f"We received a request to reset your password. Use the verification code below:\n\n"
        f"{verification_code}\n\n"
        f"This code will expire in 15 minutes.\n\n"
        f"If you didn't request this, please ignore this email.\n\n"
        f"Thank you,\nThe {getattr(settings, 'SITE_NAME', 'Your Site Name')} Team"
    )
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
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
        p.drawString(50, y, f"Candidate Name: Johnny Gait")
        y -= 20
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
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_jobs_for_user(request):
    try:
        from job.services.job_sync_service import JobSyncService
        synced_jobs = JobSyncService.sync_jobs_for_user(request.user)
        serializer = JobSerializer(synced_jobs, many=True)
        return Response({
            'message': f'Successfully synced {len(synced_jobs)} jobs',
            'jobs': serializer.data
        })
    except Exception as e:
        return Response({'error': f'Failed to sync jobs: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST)

from django.db import connection
from companies.services.company_sync_service import CompanySyncService


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def debug_companies(request):
    try:
        recruiter = request.user
        print(f"Debugging companies for recruiter: {recruiter.email}")
        
        all_companies = Company.objects.all()
        print(f"Total companies in database: {all_companies.count()}")
        
        recruiter_companies = Company.objects.filter(recruiter=recruiter)
        print(f"Companies for this recruiter: {recruiter_companies.count()}")
        
        other_companies = Company.objects.exclude(recruiter=recruiter)
        print(f"Companies for other recruiters: {other_companies.count()}")
        
        data = {
            'recruiter_email': recruiter.email,
            'total_companies_in_db': all_companies.count(),
            'companies_for_recruiter': recruiter_companies.count(),
            'companies_for_others': other_companies.count(),
            'companies': []
        }
        
        for company in all_companies:
            data['companies'].append({
                'id': company.company_id,
                'name': company.company_name,
                'odoo_id': company.odoo_company_id,
                'recruiter_id': company.recruiter.id,
                'recruiter_email': company.recruiter.email,
                'is_current_user': company.recruiter == recruiter
            })
        
        return Response(data)
    except Exception as e:
        print(f"Error in debug_companies: {str(e)}")
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def verify_companies(request):
    try:
        recruiter = request.user
        
        companies = Company.objects.filter(recruiter=recruiter)
        
        queries = connection.queries
        
        data = {
            'recruiter': {
                'id': recruiter.id,
                'email': recruiter.email
            },
            'query_count': len(queries),
            'last_query': queries[-1]['sql'] if queries else None,
            'companies_count': companies.count(),
            'companies': []
        }
        
        for company in companies:
            data['companies'].append({
                'id': company.company_id,
                'name': company.company_name,
                'recruiter_id': company.recruiter.id,
                'recruiter_email': company.recruiter.email,
                'is_current_user': company.recruiter == recruiter
            })
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_companies(request):
    try:
        synced_companies = CompanySyncService.sync_recruiter_companies(request.user)
        serializer = CompanySerializer(synced_companies, many=True)
        return Response({
            'message': f'Successfully synced {len(synced_companies)} companies',
            'companies': serializer.data
        })
    except Exception as e:
        return Response({'error': f'Failed to sync companies: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def debug_db_state(request):
    try:
        recruiter = request.user
        
        companies = Company.objects.filter(recruiter=recruiter)
        
        from django.db import connection
        with connection.cursor() as cursor:
            if 'sqlite' in connection.settings_dict['ENGINE']:
                cursor.execute("SELECT seq FROM sqlite_sequence WHERE name='companies_company'")
                row = cursor.fetchone()
                next_pk = row[0] if row else None
            else:
                try:
                    cursor.execute("SELECT last_value FROM companies_company_company_id_seq")
                    row = cursor.fetchone()
                    next_pk = row[0] if row else None
                except:
                    next_pk = None
        
        max_id = companies.aggregate(models.Max('company_id'))['company_id__max']
        
        data = {
            'recruiter': {
                'id': recruiter.id,
                'email': recruiter.email
            },
            'next_primary_key': next_pk,
            'max_company_id': max_id,
            'companies_count': companies.count(),
            'companies': []
        }
        
        for company in companies:
            data['companies'].append({
                'id': company.company_id,
                'name': company.company_name,
                'odoo_id': company.odoo_company_id,
                'created_at': company.created_at
            })
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reset_company_sequence(request):
    try:
        from django.db import connection
        
        max_id = Company.objects.aggregate(models.Max('company_id'))['company_id__max'] or 0
        
        with connection.cursor() as cursor:
            if 'sqlite' in connection.settings_dict['ENGINE']:
                cursor.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (max_id, 'companies_company'))
            else:
                cursor.execute("ALTER SEQUENCE companies_company_company_id_seq RESTART WITH %s", [max_id + 1])
        
        return Response({
            'message': f'Company sequence reset to {max_id + 1}',
            'max_id': max_id
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_companies(request):
    try:
        recruiter = request.user
        print(f"Fetching companies for recruiter: {recruiter.email} (ID: {recruiter.id})")
        
        companies = Company.objects.filter(recruiter=recruiter)
        print(f"Found {companies.count()} companies in database for this recruiter")
        
        for company in companies:
            print(f"Company ID: {company.company_id}, Name: {company.company_name}")
        
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data)
    except Exception as e:
        print(f"Error in get_companies: {str(e)}")
        return Response({'error': f'Failed to retrieve companies: {str(e)}'}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_odoo_credentials(request):
    if not request.user.is_active:
        return Response({'error': 'User account is disabled'}, status=status.HTTP_403_FORBIDDEN)
    
    db_url = request.data.get('db_url')
    db_name = request.data.get('db_name')
    email = request.data.get('email')
    api_key = request.data.get('api_key')
    
    if not all([db_url, db_name, email, api_key]):
        return Response({'error': 'All fields (db_url, db_name, email, api_key) are required'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    if OdooCredentials.objects.filter(recruiter=request.user, db_name=db_name).exists():
        return Response({'error': 'Credentials for this database already exist'}, 
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
    
    credentials = OdooCredentials.objects.create(
        recruiter=request.user,
        odoo_user_id=odoo_user_id,
        api_key=api_key, 
        email_address=email,
        db_name=db_name,
        db_url=db_url,
    )
    
    try:
        odoo_companies = odoo_service.get_user_companies()
        print(f"Found {len(odoo_companies)} companies in Odoo for user {request.user.email}")
        
        existing_companies = Company.objects.filter(recruiter=request.user)
        print(f"Found {existing_companies.count()} existing companies for this recruiter")
        
        created_companies = []
        
        for odoo_company in odoo_companies:
            print(f"Processing Odoo company: {odoo_company}")
            company_name = odoo_company['name']
            
            existing_company = existing_companies.filter(company_name=company_name).first()
            
            if existing_company:
                print(f"Found existing company by name: {existing_company.company_name} (ID: {existing_company.company_id})")
                existing_company.odoo_credentials = credentials
                existing_company.save()
                created_companies.append(existing_company)
            else:
                print(f"Creating new company: {company_name}")
                comp = Company.objects.create(
                    company_name=company_name,
                    recruiter=request.user,
                    odoo_credentials=credentials,
                    is_active=True
                )
                print(f"Created new company with ID: {comp.company_id}")
                created_companies.append(comp)
                
    except Exception as e:
        print(f"Error syncing companies: {str(e)}")
        return Response({'error': f'Failed to retrieve companies: {str(e)}'}, 
                        status=status.HTTP_400_BAD_REQUEST)
    
    serializer = OdooCredentialsSerializer(credentials)
    companies_serializer = CompanySerializer(created_companies, many=True)
    
    return Response({
        'message': 'Odoo credentials added successfully',
        'credentials': serializer.data,
        'companies': companies_serializer.data
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def sync_jobs_handle_duplicates(request):
    try:
        from job.services.job_sync_service import JobSyncService
        
        recruiter = request.user
        odoo_creds = OdooCredentials.objects.filter(recruiter=recruiter).last()
        if not odoo_creds:
            return Response({'error': 'No Odoo credentials found'}, status=status.HTTP_400_BAD_REQUEST)
        
        odoo_service = OdooService(
            db_url=odoo_creds.db_url,
            db_name=odoo_creds.db_name,
            email=odoo_creds.email_address,
            api_key=odoo_creds.get_api_key()
        )
        
        if not odoo_service.authenticate():
            return Response({'error': 'Failed to authenticate with Odoo'}, status=status.HTTP_400_BAD_REQUEST)
        
        odoo_jobs = odoo_service.get_jobs(user_id=odoo_creds.odoo_user_id)
        synced_jobs = []
        skipped_jobs = []
        
        companies = Company.objects.filter(recruiter=recruiter)
        
        company_map = {}
        for company in companies:
            if company.company_name not in company_map:
                company_map[company.company_name] = company
        
        duplicate_companies = {}
        for company in companies:
            if company.company_name in duplicate_companies:
                duplicate_companies[company.company_name] += 1
            else:
                duplicate_companies[company.company_name] = 1
        
        for odoo_job in odoo_jobs:
            job_company_name = None
            
            if odoo_job.get('company_id') and isinstance(odoo_job['company_id'], list):
                job_company_name = odoo_job['company_id'][1]
            
            if not job_company_name:
                skipped_jobs.append({
                    'job_title': odoo_job.get('name'),
                    'reason': 'No company name found'
                })
                continue
            
            if job_company_name not in company_map:
                skipped_jobs.append({
                    'job_title': odoo_job.get('name'),
                    'company_name': job_company_name,
                    'reason': 'Company not found in database'
                })
                continue
            
            company = company_map[job_company_name]
            
            is_duplicate = duplicate_companies.get(job_company_name, 0) > 1
            
            job, created = Job.objects.update_or_create(
                company=company,
                job_title=odoo_job['name'],
                defaults={
                    'job_description': odoo_job.get('description', ''),
                    'state': odoo_job.get('state', 'open'),
                    'expired_at': timezone.now() + timedelta(days=365)
                }
            )
            
            synced_jobs.append({
                'job': job,
                'created': created,
                'company_name': job_company_name,
                'is_duplicate_company': is_duplicate
            })
        
        return Response({
            'message': f'Successfully synced {len(synced_jobs)} jobs, skipped {len(skipped_jobs)} jobs',
            'synced_jobs': JobSerializer([item['job'] for item in synced_jobs], many=True).data,
            'sync_details': synced_jobs,
            'skipped_jobs': skipped_jobs
        })
    except Exception as e:
        return Response({'error': f'Failed to sync jobs: {str(e)}'},
                        status=status.HTTP_400_BAD_REQUEST)