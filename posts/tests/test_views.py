from tests.fixtures.fixture_data import group
import posts
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from posts.models import Comment, Follow, Post, Group
from django.urls import reverse
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile


User = get_user_model()


def count_object_plus_one(model):
    def test_count(test_func):
        def wrapper(*args_inner):
            count = model.objects.count()
            test_func(*args_inner)
            args_inner[0].assertEqual(count + 1, model.objects.count())
            return test_func
        return wrapper
    return test_count


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

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        file = (
            b'\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x01\x00\x3b'
        )
        cls.image = SimpleUploadedFile(
            'small.gif', small_gif, content_type='image/gif')
        cls.some_file = SimpleUploadedFile(
            'file.doc', file, content_type='file/doc')
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

    @count_object_plus_one(Post)
    def test_add_post_in_group(self):
        """Tets add post in group."""
        post = Post.objects.create(
            text='Это новый пост',
            author=self.user,
            group=self.group_old)
        response = self.authorized_client.get(
            reverse('group', args=[self.group_old.slug]))
        self.assertContains(response, post.text, status_code=200)

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

    @count_object_plus_one(Post)
    def test_is_new_post_after_publication(self):
        """After add the post must be on the
        general, profil, post and group pages."""
        self.authorized_client.post(
            reverse('new_post'),
            self.data_new_publication,
            follow=True)
        cache.clear()
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

    def query_follow(self, client):
        return client.get(reverse('profile_follow',
                                  args=[self.user_for_follow]))

    def query_add_comment(self, client):
        client.post(reverse(
            'add_comment',
            args=[self.user_for_follow, self.post_for_comment.id]),
            data={'post': self.post_for_comment,
                  'author': self.user,
                  'text': 'Comment from authorized client'})

    def query_remove_follow(self, client):
        return client.get(reverse(
            'profile_unfollow',
            args=[self.user_for_follow]))

    def test_unauthorized_client_follow(self):
        """Test add follow unauthorized client."""
        count_follow = self.user.follower.count()
        count_following = self.user_for_follow.following.count()
        response = self.query_follow(self.unauthorized_client)
        self.assertEqual(count_follow, self.user.follower.count())
        self.assertEqual(
            count_following, self.user_for_follow.following.count())
        self.assertRedirects(
            response,
            (f"{reverse('login')}?next=" +
             f"{reverse('profile_follow', args=[self.user_for_follow])}"),
            status_code=302, target_status_code=200)

    def test_authorized_client_follow(self):
        """Test add follow authorized client."""
        count_follow = self.user.follower.count()
        count_following = self.user_for_follow.following.count()
        self.query_follow(self.authorized_client)
        self.assertEqual(Follow.objects.first().user, self.user)
        self.assertEqual(Follow.objects.first().author, self.user_for_follow)
        self.assertEqual(count_follow + 1, self.user.follower.count())
        self.assertEqual(count_following + 1,
                         self.user_for_follow.following.count())

    def test_unauthorized_client_remove_follow(self):
        """Test remove follow unauthorized client."""
        count_follow = Follow.objects.count()
        response = self.query_remove_follow(self.unauthorized_client)
        self.assertEqual(count_follow, Follow.objects.count())
        self.assertRedirects(
            response,
            (f"{reverse('login')}?next=" +
             f"{reverse('profile_unfollow', args=[self.user_for_follow])}"),
            status_code=302, target_status_code=200)

    def test_authorized_client_remove_follow(self):
        """Test remove follow authorized client."""
        count_follow = Follow.objects.count()
        Follow.objects.create(user=self.user, author=self.user_for_follow)
        self.assertEqual(count_follow + 1, Follow.objects.count())
        self.query_remove_follow(self.authorized_client)
        self.assertEqual(count_follow, Follow.objects.count())

    def test_new_post_following(self):
        """Test new post of chosen author in my follow-index page."""
        self.query_follow(self.authorized_client)
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertContains(response, 'New post')

    def test_new_post_following_absent(self):
        """Test new post is not my follow-index page if i haven't follower."""
        response = self.authorized_client.get(reverse('follow_index'))
        self.assertNotContains(response, 'New post')

    def test_unauthorized_client_comment_post(self):
        """Test add comment unauthorized client."""
        count_comment = Comment.objects.count()
        self.query_add_comment(self.unauthorized_client)
        self.assertEqual(count_comment, Comment.objects.count())

    @count_object_plus_one(Comment)
    def test_authorized_client_comment_post(self):
        """Test add comment authorized client."""
        self.query_add_comment(self.authorized_client)
        comment = Comment.objects.first()
        self.assertEqual(comment.text, 'Comment from authorized client')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post_for_comment)

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

    @count_object_plus_one(Post)
    def test_create_post_with_img(self):
        """Test create post with image on all pages."""
        post = Post.objects.create(text='Этот с картинкой!',
                                   author=self.user,
                                   group=self.group_new,
                                   image=self.image)
        cache.clear()
        self.authorized_client.get(reverse('index'))
        self.check_publication('<img class="card-img', post.id)

    def test_create_post_with_not_img_format(self):
        """Test create posts with wrong image format."""
        response = self.authorized_client.post(
            reverse('new_post'),
            data={'text':
                  'some text',
                  'image': self.some_file})
        self.assertFormError(response, 'form', 'image',
                             [('Загрузите правильное изображение.'
                               ' Файл, который вы загрузили,'
                               ' поврежден или не является изображением.')])

    def test_cache(self):
        """Test cache page index."""
        response_old = self.authorized_client.get(reverse('index'))
        self.authorized_client.post(
            reverse('new_post'), self.data_new_publication, follow=True)
        response_new = self.authorized_client.get(reverse('index'))
        self.assertEqual(response_old.content, response_new.content)
        cache1 = cache.get(self.key)
        self.assertIn(self.data_new_publication['text'], cache1)

    def test_clear_test(self):
        """Test update date aftef clear cache on page."""
        response_old = self.authorized_client.get(reverse('index'))
        Post.objects.create(text='test_clear_cache', author=self.user)
        cache.clear()
        response_new = self.authorized_client.get(reverse('index'))
        self.assertNotEqual(response_old.content, response_new.content)
        self.assertContains(response_new, 'test_clear_cache')
