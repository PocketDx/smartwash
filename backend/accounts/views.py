from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema  # <-- Importamos extend_schema

from .serializers import LoginSerializer, UserSerializer


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    #! Crea la sesion de Django. El navegador recibe la cookie de sesion.

    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: UserSerializer, 401: dict},
        summary="Iniciar sesión",
    )
    def post(self, request):
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(request, **data.validated_data)
        if user is None:
            return Response(
                {"detail": "Credenciales invalidas."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    @extend_schema(
        request=None,
        responses={204: None},
        summary="Cerrar sesión",
    )
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeView(APIView):
    """Usuario autenticado. Endpoint privado: responde 403 si no hay sesion.

    Ademas siembra la cookie csrftoken, que el frontend necesita antes del login.
    """

    @extend_schema(
        responses={200: UserSerializer},
        summary="Obtener usuario actual",
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)
