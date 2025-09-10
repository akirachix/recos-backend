from rest_framework import viewsets
from .models import Candidate
from ..api.serializers import CandidateSerializer

class CandidateViewSet(viewsets.ModelViewSet):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
