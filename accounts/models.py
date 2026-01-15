from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from accounts.managers import UserManager


class User(AbstractBaseUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100, unique=False)
    profile_image = models.URLField(max_length=200, blank=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True


class SocialAccount(models.Model):
    class Provider(models.TextChoices):
        KAKAO = "kakao", "Kakao"
        GOOGLE = "google", "Google"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_accounts")
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_oid = models.CharField(max_length=255, help_text="카카오_oid, 구글_sub 등 소셜 서비스 고유 ID")

    class Meta:
        unique_together = ("provider", "provider_user_oid")

    def __str__(self):
        return f"{self.provider} - {self.provider_user_oid}"
