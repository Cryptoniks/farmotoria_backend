from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class PlayerProfileSerializer(serializers.ModelSerializer):
    exp_to_next = serializers.IntegerField(read_only=True)
    exp_progress = serializers.SerializerMethodField()

    class Meta:
        from ..models import PlayerProfile
        model = PlayerProfile
        fields = ("coins_balance", "level", "exp", "exp_to_next", "exp_progress")

    def get_exp_progress(self, obj):
        """Процент прогресса до следующего уровня (0-100)."""
        if obj.level >= 100:
            return 100
        needed = obj.required_exp_for_level(obj.level)
        if needed == 0:
            return 100
        return min(int((obj.exp / needed) * 100), 100)
