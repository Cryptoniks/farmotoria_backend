from django.contrib.auth.models import User
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from ..models import PlayerProfile, ensure_user_skills
from ..serializers import RegisterSerializer, PlayerProfileSerializer


class FarmotoriaPingView(APIView):
    def get(self, request):
        return Response({"project": "Farmotoria", "message": "pong"})


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = PlayerProfile.objects.get_or_create(user=request.user)
        user_skills = ensure_user_skills(request.user)

        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "coins_balance": profile.coins_balance,
            "level": profile.level,
            "exp": profile.exp,
            "exp_to_next": profile.exp_to_next,
            "exp_progress": min(int((profile.exp / profile.exp_to_next) * 100), 100) if profile.exp_to_next > 0 else 100,
            "skills": [
                {
                    "id": us.id,
                    "name": us.skill.name,
                    "level": us.level,
                    "exp": us.exp,
                    "exp_to_next": us.exp_to_next,
                    "max_level": us.skill.max_level,
                    "effect_name": us.skill.effect_name,
                    "effect_value_per_level": us.skill.effect_value_per_level,
                }
                for us in user_skills
            ],
        })
