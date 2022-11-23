from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User


class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.guest_client = Client()
        cls.authoriz_client = Client()
        cls.authoriz_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='ss',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_urls_for_all_users(self):
        """
        запрос к страницам доступен всем пользователям,
        и шаблоны существуют.
        """
        user = URLTests.user
        post = URLTests.post
        group = URLTests.group
        templates_url_names = {
            'posts/index.html': reverse('posts:index'),
            'posts/group_list.html': reverse(
                'posts:group_list',
                kwargs={'slug': group.slug}
            ),
            'posts/profile.html': reverse(
                'posts:profile',
                kwargs={'username': user}
            ),
            'posts/post_detail.html': reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id}
            ),
            'users/login.html': reverse('users:login'),
        }
        for template, address in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authoriz_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_for_edit_by_author(self):
        """
        запрос к страницам доступный только автору
        """
        post = URLTests.post
        self.user = User.objects.create_user(username='NotTheAuthor')
        self.authoriz_client.force_login(self.user)
        response = self.authoriz_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': post.id}
            ),
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': post.id}
        ),
        )

    def test_urls_not_exists(self):
        """
        запрос к несуществующей странице вернёт ошибку 404.
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_only_for_autoriz_users(self):
        """
        запрос к страницам доступным только авторизованным пользователям
        """
        response = self.guest_client.get(reverse('posts:post_create'))
        self.assertRedirects(response,
                             reverse('users:login')
                             + '?next='
                             + reverse('posts:post_create')
                             )
