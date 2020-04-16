from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from storages.backends.s3boto3 import S3Boto3Storage

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            try:
                user = User.objects.get(username=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class MediaStorageBackend(S3Boto3Storage):
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False
