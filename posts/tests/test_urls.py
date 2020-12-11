from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.unauthorized_client = Client()
        cls.data_user = {'first_name': 'Alex', 'last_name': 'Borisov',
                         'username': 'Lev',
                         'email': 'Leha@yandex.ru',
                         'password1': 'qqwweerrtt1122',
                         'password2': 'qqwweerrtt1122',
                         }

    def test_homepage(self):
        """Test access a general page for authorized client."""
        response = self.authorized_client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_force_login(self):
        """Test access a page's create new post for authorized client."""
        response = self.authorized_client.get(reverse('new_post'))
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_user_newpage(self):
        """Test if unauthorized user can create a new post."""
        response = self.unauthorized_client.get(
            reverse('new_post'), follow=False)
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('new_post')}",
            status_code=302, target_status_code=200)

    def test_redirect_after_registration(self):
        """Test redirect after registrations to /auth/login/"""
        response = self.unauthorized_client.post(
            reverse('signup'), self.data_user, follow=True)
        self.assertRedirects(response, reverse('login'),
                             status_code=302, target_status_code=200)

    def test_create_profile_after_registration(self):
        """After registration must create users's profil."""
        self.unauthorized_client.post(
            reverse('signup'), self.data_user, follow=False)
        response = self.unauthorized_client.get(
            reverse('profile', args=[self.data_user['username']]))
        self.assertContains(
            response,
            self.data_user['first_name'],
            status_code=200)
        self.assertContains(
            response,
            self.data_user['last_name'],
            status_code=200)
        self.assertContains(
            response,
            '@' +
            self.data_user['username'],
            status_code=200)
