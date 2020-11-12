from attr import fields
from django import forms
from .models import Post, Group, Comment, Message, models
from django.core.validators import ValidationError
from django.forms import Textarea


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            "group": "Группа",
            "text": "Текст",
            "image": "Картинка",
        }
        help_texts = {
            'group': ("Группа,в которую"
                      " публикуется сообщение"),
            "text": "Ваше собщение",
            "image": "Картинка к посту",
        }

    def clean_group(self):
        group = self.cleaned_data['group']

        if group:
            if(not Group.objects.filter(title=group).exists()):
                raise ValidationError("Некорректная группа")

        return group

    def clean_text(self):
        text = self.cleaned_data['text']

        if 'python-зло' in text:
            raise ValidationError("Такого не может быть!")

        return text


class CommentForm(forms.ModelForm):
    """"""
    class Meta:
        model = Comment
        fields = ('text',)
        widgets = {
            'text': Textarea(attrs={'rows': 3}),
        }


class MessageForm(forms.ModelForm):
    """"""
    class Meta:
        model = Message
        fields = ('text', 'user_to', 'user_from')
        widgets = {
            'text': Textarea(attrs={'rows': 3}),
        }
