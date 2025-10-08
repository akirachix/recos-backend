
import os
from pdfminer.high_level import extract_text as pdfminer_extract_text 
from docx import Document
import openpyxl
import tempfile
import pptx



def extract_text_from_file(file_field):
    """
    Extract text from a Django FileField object (which can be from Supabase or local).
    """
    if not file_field:
        return "No file provided."

   
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        file_field.seek(0) 
        for chunk in file_field.chunks():
            temp_file.write(chunk)
        
        temp_file_path = temp_file.name

    try:
        file_ext = os.path.splitext(file_field.name)[1].lower()
        
        if file_ext == '.pdf':
            return _extract_pdf_text(temp_file_path) 
        elif file_ext in ['.doc', '.docx']:
            return extract_docx_text(temp_file_path)
        elif file_ext == '.txt':
            return extract_txt_text(temp_file_path)
        elif file_ext in ['.xls', '.xlsx']:
            return extract_excel_text(temp_file_path)
        elif file_ext in ['.ppt', '.pptx']:
            return extract_pptx_text(temp_file_path)
        else:
            return f"Unsupported file type: {file_ext}"
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def _extract_pdf_text(file_path): 
    """Extract text from PDF files using pdfminer."""
    try:
        
        return pdfminer_extract_text(file_path)
    except Exception as e:
      
        raise Exception(f"Failed to extract text from PDF {file_path}: {str(e)}")

def extract_docx_text(file_path):
    """Extract text from DOCX files"""
    try:
        doc = Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX {file_path}: {str(e)}")

def extract_txt_text(file_path):
    """Extract text from TXT files"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()
        except Exception as e:
            raise Exception(f"Failed to extract text from TXT {file_path} with latin-1 encoding: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to read TXT file {file_path}: {str(e)}")

def extract_excel_text(file_path):
    """Extract text from Excel files"""
    try:
        workbook = openpyxl.load_workbook(file_path, read_only=True)
        text = []
        for sheet in workbook:
            for row in sheet.iter_rows(values_only=True):
                row_text = [str(cell) if cell is not None else "" for cell in row]
                text.append("\t".join(row_text))
        return "\n".join(text)
    except Exception as e:
        raise Exception(f"Failed to extract text from Excel {file_path}: {str(e)}")

def extract_pptx_text(file_path):
    """Extract text from PowerPoint files"""
    try:
        prs = pptx.Presentation(file_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)
    except Exception as e:
        raise Exception(f"Failed to extract text from PowerPoint {file_path}: {str(e)}")