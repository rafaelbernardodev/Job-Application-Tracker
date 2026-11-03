import random
from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tracker.models import Application, Company

Status = Application.Status
Source = Application.Source

COMPANIES = [
    ("Nimbus Labs", "SaaS"), ("Brightwave", "Fintech"), ("Greenfield Analytics", "Data"),
    ("Pixelforge", "Gaming"), ("Northwind Logistics", "Logistics"), ("Helix Health", "Healthtech"),
    ("Orbit Commerce", "E-commerce"), ("Lumen Education", "Edtech"), ("Cobalt Security", "Cybersecurity"),
    ("Tidal Media", "Media"), ("Ferrous Robotics", "Robotics"), ("Quartz Insurance", "Insurtech"),
    ("Mosaic Software", "Consulting"), ("Skyline Travel", "Travel"), ("Atlas Energy", "Energy"),
    ("Kite Payments", "Fintech"), ("Harbor Retail", "Retail"), ("Vertex AI", "AI"),
    ("Cedar Systems", "Consulting"), ("Pulse Fitness", "Consumer"),
]

TITLES = [
    "Junior Python Developer", "Backend Developer", "Junior Full-Stack Developer",
    "Software Engineer I", "Django Developer", "Data Analyst",
    "Junior Data Engineer", "Python Developer", "Junior Software Developer",
]

LOCATIONS = ["Recife, PE", "São Paulo, SP", "Remote - Brazil", "Remote - LATAM", "Lisbon, PT"]

SKILLS = [
    "Python", "Django", "REST APIs", "PostgreSQL", "Docker", "Git", "pandas",
    "TypeScript", "React", "AWS", "pytest", "SQL", "FastAPI", "Linux", "CI/CD",
]

SALARIES = ["", "", "R$ 4k-6k", "R$ 5k-7k", "R$ 6k-8k", "$1.5k-2.5k/mo"]

SOURCE_WEIGHTS = {
    Source.LINKEDIN: 40, Source.COMPANY_SITE: 20, Source.JOB_BOARD: 20,
    Source.REFERRAL: 10, Source.OTHER: 10,
}

# Chance that a company responds at all (anything other than silence/auto-rejection)
RESPONSE_RATE = {
    Source.REFERRAL: 0.65, Source.COMPANY_SITE: 0.25, Source.LINKEDIN: 0.15,
    Source.JOB_BOARD: 0.12, Source.OTHER: 0.10,
}


def simulate_history(application, rng, now):
    """Walk an application through the funnel, stopping once we reach 'now'."""
    t = application.events.first().occurred_at

    def advance(status, min_days, max_days):
        nonlocal t
        t = t + timedelta(days=rng.randint(min_days, max_days), hours=rng.randint(0, 8))
        if t > now:
            return False  # this step hasn't "happened yet"
        application.change_status(status, occurred_at=t)
        return True

    if rng.random() >= RESPONSE_RATE[application.source]:
        # No real response: auto-rejection or silence
        if rng.random() < 0.5:
            advance(Status.REJECTED, 3, 20)
        else:
            advance(Status.GHOSTED, 21, 35)
        return

    if not advance(Status.SCREENING, 2, 10):
        return
    if rng.random() >= 0.55:
        advance(Status.REJECTED, 2, 8)
        return
    if not advance(Status.INTERVIEW, 3, 12):
        return
    if rng.random() < 0.30:
        advance(Status.OFFER, 5, 14)
    else:
        advance(Status.REJECTED, 3, 10)


class Command(BaseCommand):
    help = "Create (or reset) a demo user with realistic job applications."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=60)
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default="demo1234")
        parser.add_argument("--seed", type=int, default=42, help="Makes the data reproducible")

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        now = timezone.now()

        user, _ = get_user_model().objects.get_or_create(username=options["username"])
        user.set_password(options["password"])
        user.save()

        # Reset: wipe this user's previous data so the command can be re-run safely
        Application.objects.filter(user=user).delete()
        Company.objects.filter(user=user).delete()

        companies = [
            Company.objects.create(user=user, name=name, industry=industry)
            for name, industry in COMPANIES
        ]

        sources = list(SOURCE_WEIGHTS)
        weights = list(SOURCE_WEIGHTS.values())

        for _ in range(options["count"]):
            source = rng.choices(sources, weights=weights)[0]
            skills = rng.sample(SKILLS, k=rng.randint(3, 6))
            application = Application.objects.create(
                user=user,
                company=rng.choice(companies),
                job_title=rng.choice(TITLES),
                source=source,
                location=rng.choice(LOCATIONS),
                work_mode=rng.choice(Application.WorkMode.values),
                salary_range=rng.choice(SALARIES),
                date_applied=(now - timedelta(days=rng.randint(0, 90))).date(),
                description_text=(
                    "We are looking for a developer to join our team. "
                    f"Requirements: {', '.join(skills)}."
                ),
            )
            simulate_history(application, rng, now)

        counts = Counter(Application.objects.filter(user=user).values_list("current_status", flat=True))
        self.stdout.write(self.style.SUCCESS(
            f"Created {options['count']} applications for '{options['username']}'"
        ))
        for status, n in counts.most_common():
            self.stdout.write(f"  {status}: {n}")