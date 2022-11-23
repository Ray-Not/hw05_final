import shutil
import tempfile

from django.core.cache import cache
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.MEDIA_ROOT)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.LIMIT = 10
        cls.user = User.objects.create_user(username='auth')
        cls.guest_client = Client()
        cls.autoriz_client = Client()
        cls.autoriz_client.force_login(cls.user)
        cls.group = Group.objects.create(
            id=1,
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            id=1,
            author=cls.user,
            text='Тестовый пост',
            group_id=1,
        )
        # Создание второго тестового пользователя
        cls.user2 = User.objects.create_user(username='auth2')
        cls.autoriz_client2 = Client()
        cls.autoriz_client2.force_login(cls.user2)
        # Создание второй тестовой группы
        Group.objects.create(
            id=2,
            title='Тестовая группа-2',
            slug='test-slug-2',
            description='Тестовое описание-2',
        )
        # Создание 20 постов с разными авторами и группами
        for i in range(2, 20):
            Post.objects.create(
                id=i,
                author=cls.user2 if (i > 9) else cls.user,
                text=f'Тестовый пост-{i}',
                group_id=1 if (i % 2) else 2,
            )

    @classmethod
    def SetUp(cls):
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        user = ViewsTests.user
        post = ViewsTests.post
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': user}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': post.id}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.autoriz_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_expected_context_with_paginator(self):
        """Передается нужный контекст в страницы с paginator"""
        username = ViewsTests.user
        group = ViewsTests.group
        posts_response = {
            Post.objects.all()[:self.LIMIT]: reverse('posts:index'),
            Post.objects.filter(author=username)[:self.LIMIT]: reverse(
                'posts:profile',
                kwargs={'username': username}
            ),
            Post.objects.filter(group_id=group.id)[:self.LIMIT]: reverse(
                'posts:group_list',
                kwargs={'slug': group.slug}
            ),
        }
        for exp_posts, response in posts_response.items():
            with self.subTest(exp_posts=exp_posts):
                response = self.autoriz_client.get(response)
                self.assertEqual(list(exp_posts),
                                 response.context.get('page_obj').object_list)

    def test_expected_context_without_paginator(self):
        """Передается нужный контекст в страницы без paginator"""
        post = ViewsTests.post
        exp_posts = Post.objects.filter(id=post.id)
        response = self.autoriz_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': post.id}),
        )
        self.assertEqual(exp_posts.get(),
                         response.context['post'])

    def test_image_get_in_context(self):
        '''Тест, что пост создается в бд и передается в контекст'''
        group = self.group
        user = self.user
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image'
        )
        # Создаём новый пост с картинкой
        post = Post.objects.create(
            text='suprom',
            author=user,
            group=group,
            image=uploaded
        )
        responses = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': user}),
            reverse('posts:group_list', kwargs={'slug': group.slug}),
        ]
        for response in responses:
            with self.subTest(response=response):
                response = self.autoriz_client.get(response)
                first_post = response.context['page_obj'][0]
                image_in_fp = first_post.image
                self.assertEqual(image_in_fp, post.image)

        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        first_post = response.context.get('post')
        image_in_fp = first_post.image
        self.assertEqual(image_in_fp, post.image)

    # def test_cache(self):
    #     Post.objects.all().delete()
    #     Post.objects.create(
    #         id=50,
    #         author=self.user,
    #         text='Тестовый пост',
    #     )
    #     response = self.autoriz_client.get(reverse('posts:index'))
    #     Post.objects.filter(id=50).delete()
    #     response2 = self.autoriz_client.get(reverse('posts:index'))
    #     self.assertEqual(response.content, response2.content)

    def test_follow_unfollow(self):
        '''
        Авторизованный пользователь может подписываться на других пользователей
        и удалять их из подписок.
        '''
        self.autoriz_client2.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user.username}
            )
        )
        self.assertTrue(Follow.objects.filter(
            author=self.user,
            user=self.user2
        )
        )
        self.autoriz_client2.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user.username}
            )
        )
        self.assertFalse(Follow.objects.filter(
            author=self.user,
            user=self.user2
        )
        )

    def test_follow_check_posts(self):
        '''
        Новая запись пользователя появляется в ленте тех, кто на него подписан
        и не появляется в ленте тех, кто не подписан.'''
        follower = User.objects.create(username='Follower')
        autoriz_client3 = Client()
        autoriz_client3.force_login(follower)
        Follow.objects.create(
            author=self.user,
            user=follower
        )
        response = autoriz_client3.get(
            reverse('posts:follow_index')
        )
        context = response.context['page_obj'].object_list
        self.assertEqual(context, list(Post.objects.filter(author=self.user)))
        self.assertNotEqual(context,
                            list(Post.objects.filter(author=self.user2)))
