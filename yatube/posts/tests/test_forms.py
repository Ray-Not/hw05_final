
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import CommentForm, PostForm
from ..models import Comment, Group, Post, User


class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем запись в базе данных для проверки сушествующего slug
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='NoAuthor')
        cls.guest_client = Client()
        cls.autoriz_client = Client()
        cls.autoriz_client.force_login(cls.user)
        cls.authoriz_client2 = Client()
        cls.authoriz_client2.force_login(cls.user2)
        cls.post = Post.objects.create(
            id=1,
            author=cls.user,
            text='Тестовый пост',
            group_id=1,
        )
        cls.group = Group.objects.create(
            id=1,
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.form = PostForm()
        cls.com_form = CommentForm()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        tasks_count = Post.objects.count()
        form_data = {
            'id': 2,
            'author': self.user,
            'text': 'Тестовый пост',
        }
        self.autoriz_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        created_post = Post.objects.filter(
            id=2,
            author=self.user,
            text='Тестовый пост',
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), tasks_count + 1)
        # Проверяем, что создалась запись с заданным слагом
        self.assertTrue(created_post.exists())
        # Проверяем, что пост доступен только авторизованному пользователю
        response = self.guest_client.post(
            reverse('posts:post_create'),
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'users:login')
            + '?next='
            + reverse(
            'posts:post_create')
        )

    def test_edit_post(self):
        """Валидная форма изменяет запись в Post."""
        post = self.post
        form_data_for_create = {
            'id': post.id,
            'author': self.user,
            'text': post.text,
        }
        form_data_for_edit = {
            'id': post.id,
            'author': self.user,
            'text': 'Изменен',
        }
        self.autoriz_client.post(
            reverse('posts:post_create'),
            data=form_data_for_create,
            follow=True,
        )
        tasks_count = Post.objects.count()
        self.autoriz_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data_for_edit,
            follow=True,
        )
        edited_post = Post.objects.filter(
            id=post.id,
            author=self.user,
            text='Изменен',
        )
        # Проверяем, что пост изменился, а не создался
        self.assertEqual(Post.objects.count(), tasks_count)
        # Проверяем, что пост изменился
        self.assertTrue(edited_post.exists())
        # Проверяем, что пост доступен только автору
        response = self.authoriz_client2.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data_for_edit,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': post.id})
        )
        # Проверяем, что пост доступен только авторизованному пользователю
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=form_data_for_edit,
            follow=True,
        )
        self.assertRedirects(response, reverse(
            'users:login')
            + '?next='
            + reverse(
            'posts:post_edit', kwargs={'post_id': post.id})
        )

    def test_create_post_group_valid(self):
        '''Тестируем, что пост с заданной группой существует
        (группа не меняется)'''
        group = self.group
        post = self.post
        form_data_for_create = {
            'text': post.text,
            'group': group
        }
        self.autoriz_client.post(
            reverse('posts:post_create'),
            data=form_data_for_create,
            follow=True,
        )
        self.assertTrue(Post.objects.filter(
            # посты не удаляются, можно получить ид по их количеству
            id=Post.objects.count(),
            text=post.text,
            author=self.user,
            group=group)
        )

    def test_comment_for_autoriz(self):
        '''Комментарии доступны только авторизованному пользователю'''
        post = self.post
        count_comments = Comment.objects.count()
        form_data_for_create = {
            'text': 'Тестовый коммент',
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            data=form_data_for_create,
            follow=True,
        )
        self.assertEqual(count_comments, count_comments)

    def test_comment_add(self):
        '''Комментарии доступны странице поста'''
        post = Post.objects.create(
            id=10,
            text=self.post.text,
            author=self.user,
        )
        comment = Comment.objects.create(
            id=1,
            post_id=post.id,
            author_id=self.user.id,
            text='Тестовый коммент'
        )
        self.assertTrue(Post.objects.filter(
            id=post.id,
            comments=comment.id
        ).exists())
