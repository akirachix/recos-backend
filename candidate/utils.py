import os
import mimetypes
import base64
from django.core.files.base import ContentFile

def save_base64_attachment(candidate, attachment_data):
    """
    Save base64 attachment data to file
    """
    try:
        base64_data = attachment_data.get('datas')
        if not base64_data:
            return None
        
        # Decode base64
        file_content = base64.b64decode(base64_data)
        
        # Get filename and extension
        original_filename = attachment_data.get('datas_fname', f"attachment_{attachment_data['id']}")
        mimetype = attachment_data.get('mimetype', 'application/octet-stream')
        
        # Determine file extension
        file_extension = get_file_extension(original_filename, mimetype)
        
        # Create safe filename
        safe_filename = create_safe_filename(original_filename, attachment_data['id'], file_extension)
        
        # Create and save attachment
        from candidate.models import CandidateAttachment
        
        attachment = CandidateAttachment(
            candidate=candidate,
            odoo_attachment_id=attachment_data['id'],
            name=attachment_data.get('name', original_filename),
            original_filename=original_filename,
            file_type=mimetype,
            file_size=len(file_content)
        )
        
        # Save the file
        attachment.file.save(safe_filename, ContentFile(file_content))
        attachment.save()
        
        return attachment
        
    except Exception as e:
        print(f"Error saving attachment: {str(e)}")
        return None

def get_file_extension(filename, mimetype):
    """Get appropriate file extension"""
    if filename:
        _, ext = os.path.splitext(filename)
        if ext:
            return ext.lower()
    
    if mimetype:
        ext = mimetypes.guess_extension(mimetype)
        if ext:
            return ext.lower()
    
    return '.bin'

def create_safe_filename(original_name, attachment_id, extension):
    """Create a safe filename for storage"""
    import re
    # Remove special characters
    clean_name = re.sub(r'[^\w\s-]', '', original_name)
    # Replace spaces with underscores
    clean_name = re.sub(r'[-\s]+', '_', clean_name)
    # Limit length
    if len(clean_name) > 50:
        clean_name = clean_name[:50]
    
    return f"att_{attachment_id}_{clean_name}{extension}"