"""
CV Generator Service - AI-powered CV tailoring for job applications.
Uses Azure OpenAI to generate tailored CVs based on job descriptions.
"""
import json
import re
import logging
from typing import Dict, List, Optional, Any

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Config
from api.schemas.job_tools import CVFormat, CVTone

logger = logging.getLogger(__name__)


# System prompt for CV generation (adapted from cv/cv_generator.py)
CV_GENERATION_SYSTEM_PROMPT = """You are a Professional CV & Resume Optimization Assistant.

## Role
You specialize in resume optimization and tailoring for job seekers across industries and seniority levels.

## Core Responsibilities
1. Analyze job description to identify:
   - Core responsibilities and requirements
   - Required and preferred skills
   - Keywords relevant to ATS and recruiters

2. Align the CV to the job description by:
   - Repositioning existing experience to emphasize relevance
   - Highlighting transferable skills
   - Optimizing keywords using the user's existing content only

## Strict Constraints (MUST Follow)
1. All edits must be based ONLY on content from the user's original CV
2. You may rewrite, reorder, condense, or emphasize - but must NOT add:
   - New responsibilities or achievements
   - New skills, tools, technologies, or certifications
   - New qualifications or metrics not in the original CV
3. Maintain complete factual accuracy at all times

## Guiding Principles
- Be concise and results-oriented
- Use strong action verbs and quantified achievements
- Prioritize clarity and scannability
- Never assume, exaggerate, or fabricate experience
"""

TONE_INSTRUCTIONS = {
    CVTone.PROFESSIONAL: "Use formal, business-appropriate language. Focus on achievements and leadership.",
    CVTone.CREATIVE: "Use engaging language while remaining professional. Highlight innovation and creative problem-solving.",
    CVTone.TECHNICAL: "Emphasize technical skills, tools, and methodologies. Use industry-specific terminology."
}


class CVGeneratorService:
    """Service for AI-powered CV generation and tailoring."""

    def __init__(self):
        self.client = self._init_client()

    def _init_client(self) -> ChatCompletionsClient:
        """Initialize Azure OpenAI client."""
        return ChatCompletionsClient(
            endpoint=Config.AZURE_AI_ENDPOINT,
            credential=AzureKeyCredential(Config.AZURE_AI_API_KEY),
        )

    def _remove_think_blocks(self, text: str) -> str:
        """Remove any <think>...</think> blocks from LLM output."""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    def _remove_markdown_wrappers(self, text: str) -> str:
        """Remove markdown code block wrappers from LLM output."""
        text = re.sub(r'^```(?:markdown|json)?\s*\n?', '', text.strip())
        text = re.sub(r'\n?```\s*$', '', text.strip())
        return text.strip()

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            patterns = [
                r'```json\s*({.*?})\s*```',
                r'```\s*({.*?})\s*```',
                r'\{.*\}'
            ]
            for pattern in patterns:
                match = re.search(pattern, response_text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1) if '```' in pattern else match.group())
                    except json.JSONDecodeError:
                        continue
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 8000) -> Optional[str]:
        """Make LLM API call with retry logic."""
        try:
            response = self.client.complete(
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=user_prompt)
                ],
                model=Config.AZURE_DEPLOYMENT,
                model_extras={"max_completion_tokens": max_tokens}
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def generate_cv(
        self,
        cv_text: str,
        job_description: str,
        format: CVFormat = CVFormat.MARKDOWN,
        tone: CVTone = CVTone.PROFESSIONAL,
        job_title: Optional[str] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a tailored CV for a specific job.

        Args:
            cv_text: User's original CV text
            job_description: Job description to tailor CV for
            format: Output format (markdown, text, json)
            tone: CV tone (professional, creative, technical)
            job_title: Optional job title for context
            company: Optional company name for context

        Returns:
            Dictionary with generated CV and metadata
        """
        # Build format-specific instructions
        format_instructions = self._get_format_instructions(format)
        tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS[CVTone.PROFESSIONAL])

        system_prompt = f"""{CV_GENERATION_SYSTEM_PROMPT}

## Tone
{tone_instruction}

## Output Format
{format_instructions}

## Job Context
{f'Job Title: {job_title}' if job_title else ''}
{f'Company: {company}' if company else ''}

Remember: Only use content from the original CV. Do not invent or exaggerate."""

        user_prompt = f"""Please optimize and tailor the following CV for this job opportunity.

## Job Description
{job_description[:10000]}

## Original CV
{cv_text[:12000]}

---

Generate the tailored CV now:"""

        try:
            response = self._call_llm(system_prompt, user_prompt, max_tokens=12000)
            if not response:
                raise ValueError("Empty response from LLM")

            # Clean the response
            cv_content = self._remove_think_blocks(response)
            cv_content = self._remove_markdown_wrappers(cv_content)

            # If JSON format requested, ensure valid JSON
            if format == CVFormat.JSON:
                try:
                    json.loads(cv_content)
                except json.JSONDecodeError:
                    # Try to extract JSON
                    parsed = self._parse_json_response(cv_content)
                    if parsed:
                        cv_content = json.dumps(parsed, indent=2)

            # Extract keywords and changes
            keywords, changes = self._analyze_changes(cv_text, cv_content, job_description)

            return {
                'cv': cv_content,
                'format': format,
                'keywords_emphasized': keywords,
                'changes_made': changes
            }

        except Exception as e:
            logger.error(f"CV generation failed: {e}")
            raise

    def _get_format_instructions(self, format: CVFormat) -> str:
        """Get format-specific output instructions."""
        if format == CVFormat.MARKDOWN:
            return """Output the CV in clean Markdown format:
- Use # for name, ## for section headers
- Use bullet points (•) for lists
- Use **bold** for emphasis
- Keep formatting clean and ATS-friendly"""

        elif format == CVFormat.TEXT:
            return """Output the CV in plain text format:
- Use UPPERCASE for section headers
- Use simple dashes (-) for bullet points
- No special formatting or markup
- Clean, readable layout"""

        elif format == CVFormat.JSON:
            return """Output the CV as a JSON object with this structure:
{
  "name": "Full Name",
  "contact": {"email": "", "phone": "", "location": "", "linkedin": ""},
  "summary": "Professional summary",
  "experience": [{"company": "", "title": "", "dates": "", "achievements": []}],
  "education": [{"institution": "", "degree": "", "year": ""}],
  "skills": ["skill1", "skill2"],
  "certifications": ["cert1", "cert2"]
}"""

        return "Output in clean, professional format."

    def _analyze_changes(
        self,
        original_cv: str,
        tailored_cv: str,
        job_description: str
    ) -> tuple[List[str], List[str]]:
        """
        Analyze what keywords were emphasized and what changes were made.

        Returns:
            Tuple of (keywords_emphasized, changes_made)
        """
        system_prompt = """Analyze the changes between an original CV and a tailored version.
Return a JSON response with:
- keywords_emphasized: list of 3-8 keywords from the job description that were emphasized in the tailored CV
- changes_made: list of 3-6 brief descriptions of key changes made (e.g., "Reframed role X to emphasize Y")

Your response MUST be valid JSON only."""

        user_prompt = f"""Original CV excerpt:
{original_cv[:3000]}

Tailored CV excerpt:
{tailored_cv[:3000]}

Job Description excerpt:
{job_description[:2000]}

Analyze the changes and return JSON:"""

        try:
            response = self._call_llm(system_prompt, user_prompt, max_tokens=1500)
            if response:
                parsed = self._parse_json_response(response)
                if parsed:
                    return (
                        parsed.get('keywords_emphasized', []),
                        parsed.get('changes_made', [])
                    )
        except Exception as e:
            logger.warning(f"Change analysis failed: {e}")

        # Return defaults on failure
        return (
            ["Relevant skills", "Experience alignment"],
            ["Tailored content for job requirements", "Optimized keywords for ATS"]
        )
