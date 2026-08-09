from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, Role


class UserModelTests(TestCase):
    def test_create_user_with_roles(self):
        admin = User.objects.create_user(
            username="admin_test", email="admin@test.com", password="password123",
            first_name="Admin", last_name="User", role=Role.ADMIN
        )
        self.assertTrue(admin.is_admin)
        self.assertFalse(admin.is_event_manager)
        self.assertFalse(admin.is_finance)
        self.assertFalse(admin.is_staff_member)

        manager = User.objects.create_user(
            username="mgr_test", email="mgr@test.com", password="password123",
            first_name="Manager", last_name="User", role=Role.EVENT_MANAGER
        )
        self.assertTrue(manager.is_event_manager)

        finance = User.objects.create_user(
            username="fin_test", email="fin@test.com", password="password123",
            first_name="Finance", last_name="User", role=Role.FINANCE
        )
        self.assertTrue(finance.is_finance)

        staff = User.objects.create_user(
            username="staff_test", email="staff@test.com", password="password123",
            first_name="Staff", last_name="User", role=Role.STAFF
        )
        self.assertTrue(staff.is_staff_member)

    def test_jwt_auth_obtain_and_refresh(self):
        user = User.objects.create_user(
            username="jwtuser", email="jwt@test.com", password="password123",
            first_name="JWT", last_name="User", role=Role.EVENT_MANAGER
        )
        client = APIClient()
        # 1. Obtain token
        resp = client.post("/api/v1/auth/login/", {"username": "jwtuser", "password": "password123"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

        # 2. Refresh token
        refresh_token = resp.data["refresh"]
        refresh_resp = client.post("/api/v1/auth/refresh/", {"refresh": refresh_token}, format="json")
        self.assertEqual(refresh_resp.status_code, 200)
        self.assertIn("access", refresh_resp.data)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="logout_user", email="logout@test.com", password="password123",
            first_name="Logout", last_name="User", role=Role.ADMIN
        )

    def test_logout_via_get(self):
        self.client.login(username="logout_user", password="password123")
        resp = self.client.get(reverse("logout"))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("login"))

    def test_logout_via_post(self):
        self.client.login(username="logout_user", password="password123")
        resp = self.client.post(reverse("logout"))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("login"))


class UserFormTests(TestCase):
    def test_user_form_new_user_requires_password_and_mandatory_fields(self):
        from apps.accounts.forms import UserForm
        form = UserForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("first_name", form.errors)
        self.assertIn("last_name", form.errors)
        self.assertIn("password", form.errors)

    def test_user_form_rejects_short_password(self):
        from apps.accounts.forms import UserForm
        form = UserForm(data={
            "username": "newguy",
            "email": "newguy@test.com",
            "first_name": "New",
            "last_name": "Guy",
            "role": Role.STAFF,
            "password": "123",
            "is_active": True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

