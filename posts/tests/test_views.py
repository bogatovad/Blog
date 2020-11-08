from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from posts.models import Post, Group
from django.urls import reverse
from io import BytesIO
from PIL import Image
from django.core.files.base import File
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

User = get_user_model()


def get_image_file(name, ext='png', size=(50, 50), color=(256, 0, 0)):
    file_obj = BytesIO()
    image = Image.new("RGBA", size=size, color=color)
    image.save(file_obj, ext)
    file_obj.seek(0)
    return File(file_obj, name=name)


class ViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.key = make_template_fragment_key('index_page')
        cls.user = User.objects.create_user(username='StasBasov')
        cls.user_for_follow = User.objects.create_user(username='Denis')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.unauthorized_client = Client()
        cls.group_old = Group.objects.create(
            title='TheCats',
            slug='Cat',
            description='We like cats very much')
        cls.group_new = Group.objects.create(
            title='TheDogs',
            slug='Dog',
            description='We like dogs very much')
        cls.data_publication = {'text': 'Это текст публикации', 'group': 1}
        cls.image = get_image_file('image.png')
        cls.data_new_publication = {
            'text': 'Это новый текст публикации!', 'group': 2}
        cls.data_new_publication_image = {
            'text': 'Это новый текст публикации!',
            'group': 2, 'image': cls.image}
        cls.data_new_publication_error_image = {
            'text': 'Формат картинки не графический',
            'group': 2, 'image': cls.image}
        cls.new_post = Post.objects.create(
            text='Это новый пост',
            author=cls.user)
        cls.post_for_comment = Post.objects.create(
            author=cls.user_for_follow, text='New post')

    def test_new_post(self):
        """Test if authorized client can add a new post."""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('new_post'), self.data_publication, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_add_post_in_group(self):
        """Tets add post in group."""
        count_posts = Post.objects.count()
        post = Post.objects.create(
            text='Это новый пост',
            author=self.user,
            group=self.group_old)
        response = self.authorized_client.get(
            reverse('group', args=[self.group_old.slug]))
        self.assertContains(response, post.text, status_code=200)
        self.assertEqual(Post.objects.count(), count_posts + 1)

    def test_change_group_in_post(self):
        """Tets change group in post."""
        post = Post.objects.create(
            text='Это старый пост',
            author=self.user,
            group=self.group_old)
        self.authorized_client.post(
            reverse('post_edit',
                    args=[self.user, post.id]),
            self.data_new_publication, follow=True)
        response = self.authorized_client.get(
            reverse('group', args=[self.group_new.slug]))
        response_old = self.authorized_client.get(
            reverse('group', args=[self.group_old.slug]))
        self.assertContains(
            response,
            self.data_new_publication['text'],
            status_code=200)
        self.assertNotContains(
            response_old,
            self.data_new_publication['text'],
            status_code=200)

    def query_post(self, user, post_id):
        return self.authorized_client.get(
            reverse('post', args=[user, post_id]))

    @staticmethod
    def query_profile(client, user):
        return client.get(reverse('profile', args=[user]))

    def choose_response_page(self, url, client, id_publication):
        return {'index': client.get(reverse('index')),
                'post': self.query_post(self.user, id_publication),
                'profile': self.query_profile(client, self.user),
                'group': client.get(reverse('group',
                                            args=[self.group_new.slug]))}[url]

    def generator_response_pages(self, client, id_publication):
        return [self.choose_response_page(url,
                                          client, id_publication) for url in (
            'index', 'post', 'profile', 'group')]

    def check_publication(self, data, id_publication):
        response_pages = self.generator_response_pages(
            self.authorized_client, id_publication)
        response_pages.extend(
            self.generator_response_pages(
                self.unauthorized_client, id_publication))

        for response in response_pages:
            self.assertContains(
                response,
                data,
                status_code=200)

    def test_is_new_post_after_publication(self):
        """After add the post must be on the
        general, profil, post and group pages."""
        posts_count = Post.objects.count()
        self.authorized_client.post(
            reverse('new_post'),
            self.data_new_publication,
            follow=True)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.check_publication(self.data_new_publication['text'], 3)

    def test_authorized_client_edit_post(self):
        """Test authorized client. It try edits the post."""
        self.authorized_client.post(
            reverse('post_edit', args=[self.user, self.new_post.id]),
            self.data_new_publication, follow=True)
        self.check_publication(
            self.data_new_publication['text'], self.new_post.id)

    def test_unauthorized_client_edit_post(self):
        """Test unauthorized client. It try edits the post."""
        response = self.unauthorized_client.post(
            reverse('post_edit', args=[self.user, self.new_post.id]),
            self.data_new_publication, follow=False)
        self.assertRedirects(
            response,
            (f"{reverse('login')}?next=" +
             f"{reverse('post_edit', args=[self.user, self.new_post.id])}"),
            status_code=302, target_status_code=200)

    def assert_follow(self, response):
        self.assertContains(response, 'Подписаться')
        self.assertContains(response, 'Подписчиков: 0')

    def assert_unfollow(self, response):
        self.assertContains(response, 'Отписаться')
        self.assertContains(response, 'Подписчиков: 1')

    def query_follow(self, client):
        client.get(reverse('profile_follow',
                           args=[self.user_for_follow]))

    def query_add_comment(self, client):
        client.post(reverse(
            'add_comment',
            args=[self.user_for_follow, self.post_for_comment.id]),
            data={'post': self.post_for_comment,
                  'author': self.user,
                  'text': 'Comment from authorized client'})

    def query_remove_follow(self, client):
        client.get(reverse('profile_unfollow', args=[self.user_for_follow]))

    def test_unauthorized_client_follow(self):
        """Test add follow unauthorized client."""
        self.query_follow(self.unauthorized_client)
        response = self.query_profile(
            self.authorized_client, self.user_for_follow)
        self.assert_follow(response)

    def test_authorized_client_follow(self):
        """Test add follow authorized client."""
        self.query_follow(self.authorized_client)
        response = self.query_profile(
            self.authorized_client, self.user_for_follow)
        self.assert_unfollow(response)

    def test_unauthorized_client_remove_follow(self):
        """Test remove follow unauthorized client."""
        self.query_remove_follow(self.unauthorized_client)
        response = self.query_profile(
            self.authorized_client, self.user_for_follow)
        self.assert_follow(response)

    def test_authorized_client_remove_follow(self):
        """Test remove follow authorized client."""
        self.query_follow(self.authorized_client)
        self.query_remove_follow(self.authorized_client)
        response = self.query_profile(
            self.authorized_client, self.user_for_follow)
        self.assert_follow(response)

    def test_new_post_following(self):
        """Test new post of chosen author in my follow-index page."""
        self.query_follow(self.authorized_client)
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertContains(response, 'New post')
        self.query_remove_follow(self.authorized_client)
        re = self.authorized_client.get(reverse('follow_index'))
        self.assertNotContains(re, 'New post')

    def test_unauthorized_client_comment_post(self):
        """Test add comment unauthorized client."""
        self.query_add_comment(self.unauthorized_client)
        response = self.query_post(
            self.user_for_follow, self.post_for_comment.id)
        self.assertNotContains(response, 'Comment from authorized client')

    def test_authorized_client_comment_post(self):
        """Test add comment authorized client."""
        self.query_add_comment(self.authorized_client)
        response = self.query_post(
            self.user_for_follow, self.post_for_comment.id)
        self.assertContains(response, 'Comment from authorized client')

    def test_404_error(self):
        """Test page not found."""
        response_group = self.authorized_client.get(
            reverse('group', args=['hello']))
        response_profil = self.authorized_client.get(
            reverse('profile', args=['kiril']))
        response_post = self.authorized_client.get(
            reverse('post', args=['kiril', '232']))

        for response in (response_group, response_profil, response_post):
            self.assertEqual(response.status_code, 404)

    def test_create_post_with_img(self):
        """Test create post with image on all pages."""
        cache.clear()
        count_posts = Post.objects.count()
        post = Post.objects.create(
            author=self.user,
            text='Это новый текст публикации!',
            group=self.group_new, image=self.image)
        self.assertEqual(count_posts + 1, Post.objects.count())
        self.check_publication('<img class="card-img"', post.id)

    def test_create_post_with_not_img_format(self):
        """Test create posts with wrong image format."""
        count_posts = Post.objects.count()
        content = (
            'Добавить запись', 'Группа', 'Текст',
            ('<input type="file" name="image"'
             ' accept="image/*" class="form-control-file" id="id_image">'),
            'Добавить')

        with open('media/file.html', 'rb') as img:
            response = self.authorized_client.post(
                reverse('new_post'),
                data={'text': 'some text', 'image': img})
            self.assertEqual(count_posts, Post.objects.count())
            self.assertEqual(response.status_code, 200)

            for data in content:
                self.assertContains(response, data)

    def test_create_post_with_img_format(self):
        """Test create post with imgage format."""
        count_posts = Post.objects.count()

        with open('media/photo.jpg', 'rb') as img:
            r = self.authorized_client.post(
                reverse('new_post'),
                data={'text': 'some text', 'image': img})
            self.assertEqual(count_posts + 1, Post.objects.count())
            self.assertEqual(r.status_code, 302)

    def test_cache(self):
        """Test cache page index."""
        response_old = self.authorized_client.get(reverse('index'))
        self.authorized_client.post(
            reverse('new_post'), self.data_new_publication, follow=True)
        response_new = self.authorized_client.get(reverse('index'))
        self.assertEqual(response_old.content, response_new.content)
        cache1 = cache.get(self.key)
        self.assertIn(self.data_new_publication['text'], cache1)
