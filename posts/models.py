from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField()
    pub_date = models.DateTimeField("date published", auto_now_add=True)

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="posts")
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, blank=True,
        null=True, related_name="posts")
    image = models.ImageField(upload_to='posts/', blank=True, null=True)

    class Meta:
        ordering = ['-pub_date']


class Comment(models.Model):
    """"""
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE,
        related_name='comments')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='comments')
    text = models.TextField()
    created = models.DateTimeField("date comment", auto_now_add=True)


class Follow(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="follower")
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="following")
    constraints = [
        models.UniqueConstraint(
            fields=['user', 'author', ], name='follow_obj'),
    ]


class Message(models.Model):
    text = models.TextField(blank=True, null=True, default=None)
    created = models.DateTimeField("date send message", auto_now_add=True)
    user_to = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="messages_to")
    user_from = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="messages_from")
