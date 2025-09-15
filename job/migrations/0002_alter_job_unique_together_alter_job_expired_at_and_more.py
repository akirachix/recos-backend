# job/migrations/0002_job_fix_expired_at.py
from django.db import migrations
from django.utils import timezone
from datetime import timedelta

class Migration(migrations.Migration):
    dependencies = [
        ('job', '0001_initial'),
    ]

    def fix_expired_at(apps, schema_editor):
        Job = apps.get_model('job', 'Job')
        # Update all records with NULL expired_at to 1 year from now
        for job in Job.objects.filter(expired_at__isnull=True):
            job.expired_at = timezone.now() + timedelta(days=365)
            job.save()

    operations = [
        migrations.RunPython(fix_expired_at),
    ]