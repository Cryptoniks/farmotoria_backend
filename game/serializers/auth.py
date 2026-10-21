from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from ..models import PlayerProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def validate(self, attrs):
        candidate = User(username=attrs.get("username"), email=attrs.get("email", ""))
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "email")


class PlayerProfileSerializer(serializers.ModelSerializer):
    exp_to_next = serializers.IntegerField(read_only=True)
    exp_progress = serializers.SerializerMethodField()

    class Meta:
        model = PlayerProfile
        fields = ("coins_balance", "level", "exp", "exp_to_next", "exp_progress")

    def get_exp_progress(self, obj):
        needed = obj.exp_to_next
        if needed == 0:
            return 100
        return min(int(obj.exp / needed * 100), 100)
