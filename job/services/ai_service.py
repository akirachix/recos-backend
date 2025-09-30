import google.genai as genai
from google.genai import types
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def generate_job_summary(job_description):
    """
    Generate a concise job summary using Google's Generative AI
    """
    try:
        if not job_description or len(job_description.strip()) < 10:
            return "Job description is too short to generate a summary."
        
        prompt = f"""
        Please generate a concise and professional job summary based on the following job description.
        The summary should highlight key responsibilities, requirements, and unique aspects of the role.
        Keep it under 150 words.

        Job Description:
        {job_description}
        
        Return the response in valid JSON format only:
        {{
            "job_summary": "generated summary text here",
            "key_responsibilities": ["responsibility 1", "responsibility 2"],
            "required_qualifications": ["qualification 1", "qualification 2"],
            "preferred_qualifications": ["qualification 1", "qualification 2"]
        }}
        """
        
        config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            max_output_tokens=1024,
            response_mime_type="application/json",
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config,
        )
        
        summary_data = parse_gemini_response(response.text)
        
        if isinstance(summary_data, dict) and 'job_summary' in summary_data:
            return summary_data['job_summary'].strip()
        else:
            logger.error(f"Unexpected response format: {summary_data}")
            return "Summary generation failed: Unexpected response format"
            
    except Exception as e:
        logger.error(f"Error generating job summary: {str(e)}")
        return f"Summary generation failed: {str(e)}"

def parse_gemini_response(response_text):
    """Parse Gemini response and extract JSON"""
    try:
        cleaned_text = response_text.strip()
        if '```json' in cleaned_text:
            cleaned_text = cleaned_text.split('```json')[1].split('```')[0].strip()
        elif '```' in cleaned_text:
            cleaned_text = cleaned_text.split('```')[1].split('```')[0].strip()
        
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse Gemini response: {response_text}")
        return {"raw_response": response_text}