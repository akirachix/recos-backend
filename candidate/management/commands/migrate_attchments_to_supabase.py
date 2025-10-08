from django.core.management.base import BaseCommand
from candidate.models import CandidateAttachment
from django.core.files.base import ContentFile
import os

class Command(BaseCommand):
    help = 'Migrates local candidate attachment files to Supabase Storage'

    def handle(self, *args, **options):
        self.stdout.write("Starting attachment migration to Supabase...")
        
        attachments = CandidateAttachment.objects.exclude(file__exact='')
        count = attachments.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No attachments found to migrate."))
            return

        for i, attachment in enumerate(count):
            try:
                if not attachment.file or not os.path.exists(attachment.file.path):
                    self.stdout.write(self.style.WARNING(f"Skipping attachment {attachment.attachment_id}: Local file not found."))
                    continue

                with attachment.file.open('rb') as f:
                    file_content = f.read()
                
                original_name = attachment.file.name

                attachment.file.save(original_name, ContentFile(file_content))
                
                self.stdout.write(self.style.SUCCESS(f"({i+1}/{count}) Migrated attachment {attachment.attachment_id}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"({i+1}/{count}) Failed to migrate attachment {attachment.attachment_id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS("Migration complete!"))