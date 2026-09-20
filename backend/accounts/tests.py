from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class AuthTests(APITestCase):
    """Cubre el contrato de autenticacion por sesion que consume el frontend."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="recepcion", password="smartwash123", rol=User.Rol.RECEPCIONISTA
        )

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 403)

    def test_me_sets_the_csrf_cookie_even_when_anonymous(self):
        # El frontend necesita el token antes de poder hacer login.
        response = self.client.get("/api/auth/me")
        self.assertIn("csrftoken", response.cookies)

    def test_login_with_valid_credentials_creates_a_session(self):
        response = self.client.post(
            "/api/auth/login",
            {"username": "recepcion", "password": "smartwash123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rol"], "recepcionista")
        self.assertIn("sessionid", response.cookies)

        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["username"], "recepcion")

    def test_login_with_invalid_credentials_is_rejected(self):
        response = self.client.post(
            "/api/auth/login", {"username": "recepcion", "password": "incorrecta"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 403)

    def test_login_without_csrf_token_is_rejected(self):
        client = APIClient(enforce_csrf_checks=True)
        client.get("/api/auth/me")  # siembra la cookie csrftoken
        response = client.post(
            "/api/auth/login",
            {"username": "recepcion", "password": "smartwash123"},
        )
        self.assertEqual(response.status_code, 403)

    def test_logout_ends_the_session(self):
        self.client.login(username="recepcion", password="smartwash123")
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 403)
