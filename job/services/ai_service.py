# job/services/ai_service.py

import json
import google.genai as genai
from google.genai import types
from django.conf import settings
from ai_reports.services.ai_analysis_service import get_genai_client, parse_gemini_response
import logging

logger = logging.getLogger(__name__)


def generate_job_summary(job_description):
    """
    Generate a summary of the job description
    """
    try:
        if not job_description or not job_description.strip():
            logger.warning("Empty job description provided")
            return "No job description available for summary generation."
        
        client = get_genai_client()
        if not client:
            logger.error("GenAI client not available")
            return "AI service is not available. Please check API configuration."
        
        prompt = f"""
        Analyze this job description and extract key information.
        
        JOB DESCRIPTION:
        {job_description}
        
        Provide a detailed summary in valid JSON format only.
        
        {{
            "job_summary": "A 2-3 sentence paragraph summarizing the role and its key responsibilities",
            "key_responsibilities": ["List of key responsibilities"],
            "required_skills": ["List of required skills"],
            "preferred_qualifications": ["List of preferred qualifications"],
            "experience_level": "entry-level/mid-level/senior-level/executive-level",
            "industry": "Industry sector",
            "job_type": "full-time/part-time/contract/etc."
        }}
        """
        
        config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config,
        )
        
        logger.info(f"Received response from GenAI: {response.text[:200]}...")
        
        # Try to parse the response
        try:
            job_data = parse_gemini_response(response.text)
        except Exception as parse_error:
            logger.error(f"Error parsing JSON response: {parse_error}")
            logger.error(f"Raw response: {response.text}")
            # Try to extract JSON manually as a fallback
            job_data = extract_json_manually(response.text)
        
        # Validate the parsed data
        if not isinstance(job_data, dict):
            logger.error(f"Parsed data is not a dictionary: {type(job_data)}")
            logger.error(f"Parsed data: {job_data}")
            return f"Error: Invalid response format. Raw response: {response.text}"
        
        # Check for required fields
        required_fields = ['job_summary', 'key_responsibilities', 'required_skills']
        missing_fields = [field for field in required_fields if field not in job_data]
        
        if missing_fields:
            logger.warning(f"Missing required fields in job data: {missing_fields}")
            # Add default values for missing fields
            for field in missing_fields:
                if field == 'job_summary':
                    job_data[field] = "Job summary not available."
                elif field == 'key_responsibilities':
                    job_data[field] = ["Key responsibilities not specified."]
                elif field == 'required_skills':
                    job_data[field] = ["Required skills not specified."]
        
        summary = format_job_summary(job_data)
        logger.info("Successfully generated job summary")
        return summary
        
    except Exception as e:
        logger.error(f"Job summary generation failed: {str(e)}")
        return f"Job summary generation failed: {str(e)}"


def extract_json_manually(text):
    """
    Manually extract JSON from text when the parser fails
    """
    try:
        # Look for JSON in the text
        start_idx = text.find('{')
        if start_idx == -1:
            return {"error": "No JSON found in response"}
        
        # Find the matching closing brace
        brace_count = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        if brace_count != 0:
            return {"error": "Unclosed JSON braces"}
        
        json_str = text[start_idx:end_idx]
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"Manual JSON extraction failed: {e}")
        return {"error": f"Manual JSON extraction failed: {e}"}


def format_job_summary(job_data):
    """Format the job data into a readable summary with equal sign separators"""
    try:
        if not isinstance(job_data, dict):
            logger.error(f"Job data is not a dictionary: {type(job_data)}")
            return "Job data not available in expected format."
        
        # Extract data with defaults
        job_summary = job_data.get('job_summary', 'No summary available.')
        key_responsibilities = job_data.get('key_responsibilities', [])
        required_skills = job_data.get('required_skills', [])
        preferred_qualifications = job_data.get('preferred_qualifications', [])
        experience_level = job_data.get('experience_level', 'Not specified')
        industry = job_data.get('industry', 'Not specified')
        job_type = job_data.get('job_type', 'Not specified')
        
        # Ensure lists are actually lists
        if not isinstance(key_responsibilities, list):
            key_responsibilities = [str(key_responsibilities)]
        if not isinstance(required_skills, list):
            required_skills = [str(required_skills)]
        if not isinstance(preferred_qualifications, list):
            preferred_qualifications = [str(preferred_qualifications)]
        
        parts = [
            "JOB SUMMARY",
            "=" * 20,
            job_summary,
            "",
            "KEY RESPONSIBILITIES",
            "=" * 20,
        ]
        
        if key_responsibilities:
            parts.extend([f"• {item}" for item in key_responsibilities if item])
        else:
            parts.append("• Not specified")
        
        parts.extend([
            "",
            "REQUIRED SKILLS",
            "=" * 20,
        ])
        
        if required_skills:
            parts.extend([f"• {item}" for item in required_skills if item])
        else:
            parts.append("• Not specified")
        
        if preferred_qualifications:
            parts.extend([
                "",
                "PREFERRED QUALIFICATIONS",
                "=" * 20,
            ])
            parts.extend([f"• {item}" for item in preferred_qualifications if item])
        
        parts.extend([
            "",
            "ADDITIONAL INFORMATION",
            "=" * 20,
            f"• Experience Level: {experience_level}",
            f"• Industry: {industry}",
            f"• Job Type: {job_type}"
        ])
        
        return "\n".join(parts)
        
    except Exception as e:
        logger.error(f"Error formatting job summary: {str(e)}")
        return f"Error formatting job summary: {str(e)}"