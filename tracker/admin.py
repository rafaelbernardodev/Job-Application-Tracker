from django.contrib import admin

from .models import Application, Company, StatusEvent

class StatusEventInline(admin.TabularInline):
    model = StatusEvent
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "industry", "user")
    search_fields = ("name",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job_title", "company", "source", "current_status", "date_applied")
    list_filter = ("current_status", "source", "work_mode")
    search_fields = ("job_title", "company__name")
    inlines = [StatusEventInline]
