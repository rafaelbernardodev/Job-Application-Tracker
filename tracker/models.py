from django.conf import settings
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils import timezone

class Company(models.Model):
  user = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="companies"
  )
  name = models.CharField(max_length=200)
  website = models.URLField(blank=True)
  industry = models.CharField(max_length=100, blank=True)
  notes = models.TextField(blank=True)

  class Meta:
    verbose_name_plural = "companies"
    constraints = [
      # "Google" and "google" count as the same company for one user
      models.UniqueConstraint(
        Lower("name"), "user", name="unique_company_name_per_user"
      )
    ]

  def __str__(self):
    return self.name

class Application(models.Model):
  class Status(models.TextChoices):
    APPLIED = "applied", "Applied"
    SCREENING = "screening", "Screening"
    INTERVIEW = "interview", "Interview"
    OFFER = "offer", "Offer"
    REJECTED = "rejected", "Rejected"
    GHOSTED = "ghosted", "Ghosted"

  class WorkMode(models.TextChoices):
    REMOTE = "remote", "Remote"
    HYBRID = "hybrid", "Hybrid"
    ONSITE = "onsite", "On-site"

  class Source(models.TextChoices):
    LINKEDIN = "linkedin", "LinkedIn"
    REFERRAL = "referral", "Referral"
    COMPANY_SITE = "company_site", "Company site"
    JOB_BOARD = "job_board", "Other job board"
    OTHER = "other", "Other"

  user = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications"
  )
  company = models.ForeignKey(
    Company, on_delete=models.CASCADE, related_name="applications"
  )
  job_title = models.CharField(max_length=200)
  source = models.CharField(max_length=20, choices=Source.choices, default=Source.OTHER)
  job_url = models.URLField(blank=True)
  location = models.CharField(max_length=200, blank=True)
  work_mode = models.CharField(max_length=10, choices=WorkMode.choices, blank=True)
  salary_range = models.CharField(max_length=100, blank=True)
  date_applied = models.DateField(default=timezone.localdate)
  description_text = models.TextField(blank=True)

  # Denormalized for fast display; StatusEvent is the source of truth
  current_status = models.CharField(
    max_length=20, choices=Status.choices, default=Status.APPLIED
  )

  class Meta:
    ordering = ["-date_applied"]

  def __str__(self):
    return f"{self.job_title} @ {self.company.name}"

  def change_status(self, new_status, notes="", occurred_at=None):
    """Record a status change and keep current_status in sync."""
    with transaction.atomic():
      event = StatusEvent.objects.create(
        application=self,
        status=new_status,
        notes=notes,
        occurred_at=occurred_at or timezone.now(),
      )
      self.current_status = new_status
      self.save(update_fields=["current_status"])
    return event

class StatusEvent(models.Model):
  application = models.ForeignKey(
    Application, on_delete=models.CASCADE, related_name="events"
  )
  status = models.CharField(max_length=20, choices=Application.Status.choices)
  occurred_at = models.DateTimeField(default=timezone.now)
  notes = models.TextField(blank=True)

  class Meta:
    ordering = ["occurred_at"]

  def __str__(self):
    return f"{self.application} → {self.status}"