from django.contrib.auth.models import User
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import ensure_user_skills
from ..serializers import MeUpdateSerializer, RegisterSerializer
from ..services.player import get_profile
from .base import GameAPIView


class FarmotoriaPingView(APIView):
    """Health check для Render."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"project": "Farmotoria", "message": "pong"})


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []


class MeView(GameAPIView):
    def get(self, request):
        profile = get_profile(request.user)
        user_skills = ensure_user_skills(request.user)
        exp_to_next = profile.exp_to_next
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "coins_balance": profile.coins_balance,
            "level": profile.level,
            "exp": profile.exp,
            "exp_to_next": exp_to_next,
            "exp_progress": min(int(profile.exp / exp_to_next * 100), 100) if exp_to_next > 0 else 100,
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

    def put(self, request):
        """Смена имени и e-mail (используется на странице профиля)."""
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.get(request)

    patch = put
