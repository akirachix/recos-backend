import json
import google.genai as genai
from google.genai import types
from django.conf import settings
from ai_reports.utils import extract_text_from_file_object
from ai_reports.services.ai_analysis_service import get_genai_client, parse_gemini_response
import logging

logger = logging.getLogger(__name__)

def generate_candidate_skill_summary(candidate):
    """
    Generate a skill summary for a candidate based on their resume attachments
    """
    try:
        resume_text = ""
        for attachment in candidate.attachments.all():
            if attachment.is_document():
                try:
                    text = extract_text_from_file_object(attachment.file)
                    resume_text += f"\n\n--- Document: {attachment.name} ---\n{text}"
                except Exception as e:
                    logger.error(f"Error extracting text from attachment {attachment.name}: {e}")
                    continue
        
        if not resume_text.strip():
            return "No resume text available for skill extraction."
        
        client = get_genai_client()
        if not client:
            return "AI service is not available. Please check API configuration."
        
        prompt = f"""
        Analyze this candidate's resume and extract a comprehensive skill summary relevant to the job they're applying for.
        
        CANDIDATE NAME: {candidate.name}
        JOB TITLE: {candidate.job.job_title}
        JOB DESCRIPTION: {candidate.job.job_description}
        
        RESUME TEXT:
        {resume_text}
        
        Provide a detailed skill summary in valid JSON format only. Focus on skills relevant to the job type, whether technical, professional, creative, administrative, or any other field. Include both hard skills and soft skills.
        
        {{
            "skills_summary": "A 2-3 sentence paragraph summarizing the candidate's most relevant skills and experience for this position",
            "key_skills": {{
                "technical_professional_skills": ["List specific technical or professional skills relevant to the job"],
                "soft_skills": ["List interpersonal and soft skills"],
                "industry_knowledge": ["List industry-specific knowledge or expertise"],
                "tools_software_equipment": ["List relevant tools, software, or equipment"],
                "certifications_licenses": ["List relevant certifications or licenses"]
            }},
            "experience": {{
                "total_years": "Estimated total years of relevant experience",
                "relevant_experience": "Brief description of most relevant experience",
                "career_level": "entry-level/mid-level/senior-level/executive-level"
            }},
            "education": {{
                "highest_degree": "Highest degree obtained",
                "field_of_study": "Field of study",
                "relevant_education": "Any education particularly relevant to the job"
            }},
            "languages": ["List languages and proficiency levels if mentioned"],
            "additional_qualifications": ["Any other relevant qualifications or achievements"]
        }}
        """
        
        config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config,
            )
            logger.info(f"Gemini API response: {response.text}")
            skill_data = parse_gemini_response(response.text)
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return f"Skill summary generation failed due to API error: {str(e)}"
        
        summary = format_skill_summary(skill_data)
        
        return summary
        
    except Exception as e:
        logger.error(f"An unexpected error occurred in generate_candidate_skill_summary: {e}")
        return f"Skill summary generation failed: {str(e)}"


def format_skill_summary(skill_data):
    """Format the skill data into a readable summary"""
    if isinstance(skill_data, dict):
        skills_summary = skill_data.get('skills_summary', '')
        key_skills = skill_data.get('key_skills', {})
        experience = skill_data.get('experience', {})
        education = skill_data.get('education', {})
        languages = skill_data.get('languages', [])
        additional_qualifications = skill_data.get('additional_qualifications', [])
        
        skills_parts = []
        for category, skills in key_skills.items():
            if skills:
                category_name = category.replace('_', ' ').title()
                skills_parts.append(f"{category_name}: {', '.join(skills)}")
        
        experience_parts = [
            f"Career Level: {experience.get('career_level', 'unknown')}",
            f"Years of Experience: {experience.get('total_years', 'unknown')}",
            f"Relevant Experience: {experience.get('relevant_experience', 'Not specified')}"
        ]
        
        education_parts = [
            f"Highest Degree: {education.get('highest_degree', 'Not specified')}",
            f"Field of Study: {education.get('field_of_study', 'Not specified')}",
            f"Relevant Education: {education.get('relevant_education', 'Not specified')}"
        ]
        
        parts = [
            "SKILLS SUMMARY",
            "=" * 20,
            skills_summary,
            "",
            "KEY SKILLS",
            "=" * 20,
            "\n".join(f"• {item}" for item in skills_parts),
            "",
            "EXPERIENCE",
            "=" * 20,
            "\n".join(f"• {item}" for item in experience_parts),
            "",
            "EDUCATION",
            "=" * 20,
            "\n".join(f"• {item}" for item in education_parts),
        ]
        
        if languages:
            parts.extend([
                "",
                "LANGUAGES",
                "=" * 20,
                f"• {', '.join(languages)}"
            ])
        
        if additional_qualifications:
            parts.extend([
                "",
                "ADDITIONAL QUALIFICATIONS",
                "=" * 20,
                f"• {', '.join(additional_qualifications)}"
            ])
        
        return "\n".join(parts)
    else:
        return "Skill data not available in expected format."