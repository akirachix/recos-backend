from django.shortcuts import render

from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authtoken.models import Token
from interviewConversation.models import InterviewConversation
from job.models import Job
from candidate.models import Candidate
from .serializers import InterviewConversationSerializer, JobSerializer, CandidateSerializer, RecruiterSerializer, OdooCredentialsSerializer, CompanySerializer
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from users.models import Recruiter, OdooCredentials
from users.services.odoo_service import OdooService
from companies.models import Company
import random
from django.utils import timezone
from datetime import timedelta


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