from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models.query import QuerySet
from django.http import request
from django.shortcuts import render, get_object_or_404, redirect
from .forms import PostForm, CommentForm, GroupForm
from .models import Post, Group, User, Follow, Message
import operator


def get_paginator(request, data: QuerySet):
    """Return a paginator.

    Keyword arguments:
    request -- HttpRequest's object
    data    -- Data that we need to split on pages

    """
    paginator = Paginator(data, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return page, paginator


def index(request):
    """This view shows the general site's page."""
    posts = Post.objects.all()
    page, paginator = get_paginator(request, posts)
    groups = Group.objects.all()
    users = User.objects.all()
    return render(
        request,
        'index.html',
        {'page': page,
         'paginator': paginator,
         'groups': groups,
         'users': users}
    )


def group_posts(request, slug: str):
    """This view shows the group's posts."""
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    page, paginator = get_paginator(request, posts)
    groups = Group.objects.all()
    users = User.objects.all()
    return render(
        request,
        "group.html",
        {"page": page, 'paginator': paginator, "group": group,
         'groups': groups, 'users': users}
    )


@login_required
def new_post(request):
    """This view add a new post."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('index')
    return render(request, 'new.html', {'form': form})


def profile(request, username: str):
    """This view shows the users's profil."""
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    page, paginator = get_paginator(request, posts)
    is_follow = author.following.filter(user=request.user.id).exists()
    return render(
        request,
        'profile.html',
        {'page': page, 'paginator': paginator,
         'author': author, 'following': is_follow}
    )


def post_view(request, username, post_id):
    """This view shows one post by post's id."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm()
    is_follow = post.author.following.filter(user=request.user.id).exists()
    return render(request, 'post.html',
                  {'author': post.author, 'post': post, 'form': form,
                   'comments': post.comments.all(), 'following': is_follow})


@login_required
def post_edit(request, username: str, post_id: int):
    """This view edits the post by its id and saves changes in database."""
    post = Post.objects.get(author__username=username, id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None, instance=post)
    if post.author != request.user:
        return redirect('post', username, post_id)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('post', username, post_id)
    return render(request, 'new.html', {"form": form,
                                        'post': post,
                                        'edit': True})


def page_not_found(request, exception):
    """Error 404: page not found."""
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    """Error 505."""
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    """Add comment under post."""
    form = CommentForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = Post.objects.get(id=post_id)
            comment.author = request.user
            comment.save()
    return redirect('post', username, post_id)


@login_required
def follow_index(request):
    """Show page with my lovely authors."""
    posts = Post.objects.filter(author__following__user=request.user)
    page, paginator = get_paginator(request, posts)
    groups = Group.objects.all()
    users = User.objects.all()
    return render(
        request,
        'follow.html',
        {'page': page,
         'paginator': paginator,
         'groups': groups,
         'users': users}
    )


@login_required
def profile_follow(request, username):
    """Create follow."""
    author = User.objects.get(username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user,
                                     author=author)
    return redirect("follow_index")


@login_required
def profile_unfollow(request, username):
    """Remove follow."""
    request.user.follower.filter(
        author=User.objects.get(username=username)).delete()
    return redirect("follow_index")


@login_required
def post_delete(request, username, post_id):
    author = User.objects.get(username=username)
    if author == request.user:
        author.posts.get(id=post_id).delete()
    return redirect('index')


def find_post(request):
    query = request.GET.get('text')
    posts = Post.objects.filter(text__icontains=query)
    page, paginator = get_paginator(request, posts)
    groups = Group.objects.all()
    users = User.objects.all()
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator, 'find': True, 'query': query,
         'groups': groups, 'users': users}
    )


@login_required
def message(request, username):
    author = get_object_or_404(User, username=username)
    messages_from = author.messages_to.filter(user_from=request.user)
    messages_to = request.user.messages_to.filter(user_from=author)
    messages = sorted(messages_to | messages_from,
                      key=operator.attrgetter('created'))
    is_follow = author.following.filter(user=request.user.id).exists()
    return render(request, 'message.html', {'author': author,
                                            'messages': messages,
                                            'following': is_follow})


@login_required
def send_message(request, username):
    author = get_object_or_404(User, username=username)
    Message.objects.create(
        user_to=request.user,
        user_from=author,
        text=request.POST.get('message'))
    return redirect('message', author.username)


def new_group(request):
    form = GroupForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('index')
    return render(request, 'new_group.html', {'form': form})
