from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
# from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User


POSTS_PER_PAGE = 10


def page_obj(request, contents):
    return Paginator(contents,
                     POSTS_PER_PAGE).get_page(request.GET.get('page'))


# @cache_page(15)
def index(request):
    return render(request, 'posts/index.html', {
        'page_obj': page_obj(request, Post.objects.all()),
    })


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    return render(request, 'posts/group_list.html', {
        'group': group,
        'page_obj': page_obj(request, group.posts.all()),
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    return render(request, 'posts/profile.html', {
        'author': author,
        'page_obj': page_obj(request, author.posts.all()),
        'following': Follow.objects.filter(
            author=author,
            user=request.user
        ),
    })


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related(
            'author',
            'group'
        ), id=post_id
    )
    comments = Comment.objects.filter(post=post)
    form = CommentForm()
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    post_form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if not post_form.is_valid():
        return render(request, 'posts/create_post.html', {'form': post_form, })
    post = post_form.save(False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', request.user)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    post_form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if post_form.is_valid():
        post_form.save()
        return redirect('posts:post_detail', post_id)
    return render(request, 'posts/create_post.html', {
        'form': post_form,
        'post': post,
    })


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post = Post.objects.filter(author__following__user=request.user)
    return render(request, 'posts/follow.html', {
        'page_obj': page_obj(request, post),
    })


@login_required
def profile_follow(request, username):
    # Подписаться на автора
    author_object = User.objects.get(username=username)
    context = {
        'following': Follow.objects.filter(
            author=author_object,
            user=request.user
        ),
        'author': author_object,
        'page_obj': page_obj(request, author_object.posts.all()),
    }
    # 2 проверка, если клиент неявно зайдет на profile/<str:username>/follow/
    if Follow.objects.filter(
        author=author_object,
        user=request.user
    ) or (request.user == author_object):
        return render(request, 'posts/profile.html', context)
    Follow.objects.create(
        author=author_object,
        user=request.user
    )
    return render(request, 'posts/profile.html', context)


@login_required
def profile_unfollow(request, username):
    # Дизлайк, отписка
    author_object = User.objects.get(username=username)
    context = {
        'following': Follow.objects.filter(
            author=author_object,
            user=request.user
        ),
        'author': author_object,
        'page_obj': page_obj(request, author_object.posts.all()),
    }
    # 2 проверка, если клиент неявно зайдет на profile/<str:username>/unfollow/
    if (not Follow.objects.filter(
        author=author_object,
        user=request.user
    )) or (request.user == author_object):
        return render(request, 'posts/profile.html', context)
    Follow.objects.filter(
        author=author_object,
        user=request.user
    ).delete()
    return render(request, 'posts/profile.html', context)
