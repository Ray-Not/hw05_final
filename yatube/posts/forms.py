from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        help_texts = {'text': 'Текст нового поста',
                      'group': 'Группа, к которой будет относиться пост'}
        labels = {'text': 'Текст поста', 'group': 'Группа'}
        fields = ['text', 'group', 'image']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
