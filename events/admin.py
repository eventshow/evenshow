from django.contrib import admin
from django.apps import apps

from events import models

# Register your models here.


class CategoryAdmin(admin.ModelAdmin):
    search_fields = ('name', 'category_events')
    exclude = ()


class EnrollmentAdmin(admin.ModelAdmin):
    search_fields = ('created_by__username', 'event__title')
    list_display = ('status', 'created_by', 'event')
    list_filter = (
        'status', ('created_by', admin.RelatedOnlyFieldListFilter), ('event__created_by', admin.RelatedOnlyFieldListFilter))


class EventAdmin(admin.ModelAdmin):
    search_fields = ('title', 'category__name', 'created_by__username')
    list_display = ('created_by', 'title', 'price', 'min_age', 'capacity', 'lang', 'pets', 'parking_nearby', 'category', 'start_day',
                    'start_time', 'end_time', 'location')
    list_filter = ('title', ('category', admin.RelatedOnlyFieldListFilter),
                   ('created_by', admin.RelatedOnlyFieldListFilter),
                   'price', 'capacity', 'lang', 'min_age')


class MessageAdmin(admin.ModelAdmin):
    search_fields = ('title',)
    list_display = ('title',)


class ProfileAdmin(admin.ModelAdmin):
    search_fields = ('user', 'token')
    list_display = ('user', 'birthdate', 'age', 'token',
                    'eventpoints', 'discount', 'avg_attendee_score', 'avg_host_score')


class RatingAdmin(admin.ModelAdmin):
    search_fields = ('reviewed__username', )
    list_display = ('score', 'created_by', 'reviewed')
    list_filter = ('score', ('created_by', admin.RelatedOnlyFieldListFilter),
                   ('reviewed', admin.RelatedOnlyFieldListFilter))


admin.site.register(models.Category, CategoryAdmin)
admin.site.register(models.Enrollment, EnrollmentAdmin)
admin.site.register(models.Event, EventAdmin)
admin.site.register(models.Message, MessageAdmin)
admin.site.register(models.Profile, ProfileAdmin)
admin.site.register(models.Rating, RatingAdmin)
