from rest_framework.test import APITestCase


class HealthTests(APITestCase):
    def test_health_is_public_and_reaches_the_database(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
