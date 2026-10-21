from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services import GameError


class GameAPIView(APIView):
    """APIView, который превращает GameError в ответ {"detail": ...}."""

    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, GameError):
            return Response(exc.as_response_data(), status=exc.status)
        return super().handle_exception(exc)


def int_param(data, name: str) -> int:
    """Целое число из request.data / query_params или GameError 400."""
    try:
        return int(data.get(name))
    except (TypeError, ValueError):
        raise GameError(f"Некорректный параметр: {name}")
