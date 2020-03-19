from django.conf import settings
from django.db import models
from django.utils.timezone import now


class Common(models.Model):
    created_at = models.DateTimeField(
        'Created at', default=now, blank=True, editable=False)
    updated_at = models.DateTimeField(
        'Updated at', default=now, blank=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_created',  blank=True, null=True, editable=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_updated', blank=True, null=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = now()
        self.updated_at = now()

        super(Common, self).save(*args, **kwargs)
