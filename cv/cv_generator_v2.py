# cv/cv_generator_v2.py
"""
CV Generator using Azure OpenAI Responses API

Supports:
- Initial CV generation from base CV + job description
- Iterative refinement with user feedback via response chaining
- Automatic context preservation through previous_response_id
"""

import logging
import re
from typing import List, Optional, Tuple

from utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


def remove_think_blocks(text: str) -> str:
    """Remove any <think>...</think> blocks (including multiline)"""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def remove_markdown_wrappers(text: str) -> str:
    """Remove markdown code block wrappers from LLM output"""
    text = re.sub(r"^```(?:markdown)?\s*\n?", "", text.strip())
    text = re.sub(r"\n?```\s*$", "", text.strip())
    return text.strip()


def clean_cv_output(text: str) -> str:
    """Clean LLM output to get pure CV content"""
    text = remove_think_blocks(text)
    text = remove_markdown_wrappers(text)
    return text


# System prompts
CV_OPTIMIZATION_SYSTEM_PROMPT = """
## Role
You are a Professional CV & Resume Optimization Assistant.

## Background
You are a specialized AI assistant focused on resume (CV) creation, optimization, and tailoring for job seekers across industries, functions, and seniority levels. You have deep knowledge of:
- Modern recruitment and hiring practices
- Applicant Tracking Systems (ATS) and keyword parsing
- Recruiter and hiring-manager screening behavior
- Industry-specific resume standards and trends

## Primary Objective
Optimize and tailor the user's CV to the provided job description to maximize interview chances—without adding or inventing experience.

## Core Responsibilities
1. Analyze the job description to identify core responsibilities, required skills, and ATS keywords
2. Analyze the CV for content quality, keyword coverage, and relevance
3. Align the CV by repositioning experience, highlighting transferable skills, and optimizing keywords

## Strict Constraints
1. All edits must be based ONLY on content in the user's CV
2. Do NOT add new skills, experiences, certifications, or achievements
3. You may rewrite, reorder, condense, or emphasize—but never fabricate
4. Maintain complete factual accuracy

## Output Format
- Return ONLY the optimized CV in Markdown format
- Use clean, professional formatting with clear section hierarchy
- Use bullet points (•) for lists
- No explanations, commentary, or rationale—just the CV
"""

CV_FORMAT_REQUIREMENTS = """
## Format Requirements

### Header (Single Line Contact)
# FULL NAME IN UPPERCASE
+61 XXX XXX XXX | email@domain.com | City, Country | linkedin.com/in/username

### Section Headers (## with UPPERCASE)
## EXECUTIVE PROFILE
[2-3 sentence paragraph, NOT bullet points]

## CORE STRENGTHS
• Strength 1
• Strength 2

## PROFESSIONAL EXPERIENCE
**Company Name** | Role Title | Location | Dates
• Achievement with metrics
• Key responsibility

## EDUCATION & CERTIFICATIONS
• **Degree** | Institution | Year

## TECHNOLOGY SKILLS
• **Category:** Skill1, Skill2, Skill3

### Rules
- Use • (bullet character) NOT - (dash)
- Profile/Summary = paragraphs, not bullets
- Employment: **Company** | Role | Location | Dates (one line)
- Quantify achievements where possible
- Most recent experience first
"""

CV_REFINEMENT_PROMPT = """
## Refinement Mode

You are continuing to refine a CV based on user feedback. You have full context from the previous generation via response chaining.

Apply ONLY the requested changes while:
- Maintaining all previous optimizations
- Keeping the same format and structure
- Not adding any information not present in the original CV

Return ONLY the refined CV in Markdown format. No explanations.
"""


class CVGeneratorV2:
    """
    CV Generator using Responses API for stateful generation and refinement.
    """

    def __init__(self):
        self.client = get_llm_client()

    def _build_system_prompt(self, job_desc: str, instructions: str = "", is_refinement: bool = False) -> str:
        """Build complete system prompt"""
        parts = []

        if is_refinement:
            parts.append(CV_REFINEMENT_PROMPT)
        else:
            parts.append(CV_OPTIMIZATION_SYSTEM_PROMPT)

        parts.append(CV_FORMAT_REQUIREMENTS)
        parts.append(f"\n## Target Job Description\n{job_desc}")

        if instructions:
            parts.append(f"\n## Additional Instructions\n{instructions}")

        return "\n".join(parts)

    def generate(
        self,
        cv_content: str,
        job_desc: str,
        instructions: str = "",
        max_tokens: int = 16384,
    ) -> Tuple[str, str]:
        """
        Generate initial optimized CV.

        Args:
            cv_content: Original CV content
            job_desc: Job description to optimize for
            instructions: Optional additional instructions
            max_tokens: Maximum output tokens

        Returns:
            Tuple of (optimized_cv, response_id)
        """
        if not cv_content.strip():
            raise ValueError("Empty CV content")

        system_prompt = self._build_system_prompt(job_desc, instructions)

        user_prompt = f"""Optimize the following CV for the job description provided.

## Original CV

{cv_content}

---

Return ONLY the optimized CV in Markdown format."""

        response = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
        )

        cleaned_cv = clean_cv_output(response.content)

        logger.info(f"Generated CV: {response.total_tokens} tokens, response_id={response.response_id}")

        return cleaned_cv, response.response_id

    def generate_cv(self, cv_content: str, job_desc: str, instructions: str = "") -> str:
        """Backward-compatible generation method returning markdown string."""
        cv_md, _ = self.generate(cv_content, job_desc, instructions)
        return cv_md

    def refine(
        self,
        job_desc: str,
        refinement_instructions: str,
        previous_response_id: str,
        max_tokens: int = 16384,
    ) -> Tuple[str, str]:
        """
        Refine a previously generated CV based on user feedback.

        Uses response chaining (previous_response_id) to maintain full context.

        Args:
            job_desc: Original job description
            refinement_instructions: User's specific improvement requests
            previous_response_id: Response ID from previous generation
            max_tokens: Maximum output tokens

        Returns:
            Tuple of (refined_cv, new_response_id)
        """
        if not refinement_instructions.strip():
            raise ValueError("Refinement instructions required")

        system_prompt = self._build_system_prompt(job_desc, is_refinement=True)

        user_prompt = f"""Please refine the CV based on these specific instructions:

{refinement_instructions}

Apply these changes while maintaining all previous optimizations.
Return ONLY the refined CV in Markdown format."""

        response = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            previous_response_id=previous_response_id,
        )

        cleaned_cv = clean_cv_output(response.content)

        logger.info(
            f"Refined CV: {response.total_tokens} tokens, "
            f"response_id={response.response_id}, "
            f"chained from={previous_response_id}"
        )

        return cleaned_cv, response.response_id

    def regenerate_with_improvements(
        self,
        cv_content: str,
        job_desc: str,
        analysis_suggestions: List[str],
        previous_response_id: Optional[str] = None,
        max_tokens: int = 16384,
    ) -> Tuple[str, str]:
        """
        Regenerate CV incorporating analysis improvement suggestions.

        Args:
            cv_content: Original CV content (for context)
            job_desc: Job description
            analysis_suggestions: List of improvements from CV analysis
            previous_response_id: Optional response ID to chain from
            max_tokens: Maximum output tokens

        Returns:
            Tuple of (improved_cv, new_response_id)
        """
        suggestions_text = "\n".join(f"- {s}" for s in analysis_suggestions)

        instructions = f"""Apply these specific improvements from CV-JD analysis:

{suggestions_text}

Incorporate all suggestions while maintaining professional tone and accurate content."""

        system_prompt = self._build_system_prompt(job_desc, instructions)

        user_prompt = f"""Regenerate the CV with the specified improvements.

## Original CV

{cv_content}

---

Apply all improvement suggestions and return ONLY the improved CV in Markdown format."""

        response = self.client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            previous_response_id=previous_response_id,
        )

        cleaned_cv = clean_cv_output(response.content)

        logger.info(f"Regenerated CV with {len(analysis_suggestions)} improvements: {response.total_tokens} tokens")

        return cleaned_cv, response.response_id


# Convenience functions
def generate_cv(cv_content: str, job_desc: str, instructions: str = "") -> Tuple[str, str]:
    """Generate optimized CV. Returns (cv_markdown, response_id)."""
    generator = CVGeneratorV2()
    return generator.generate(cv_content, job_desc, instructions)


def refine_cv(job_desc: str, refinement_instructions: str, previous_response_id: str) -> Tuple[str, str]:
    """Refine CV based on user feedback. Returns (cv_markdown, response_id)."""
    generator = CVGeneratorV2()
    return generator.refine(job_desc, refinement_instructions, previous_response_id)


def regenerate_cv_with_improvements(
    cv_content: str, job_desc: str, analysis_suggestions: List[str], previous_response_id: Optional[str] = None
) -> Tuple[str, str]:
    """Regenerate CV with analysis suggestions. Returns (cv_markdown, response_id)."""
    generator = CVGeneratorV2()
    return generator.regenerate_with_improvements(cv_content, job_desc, analysis_suggestions, previous_response_id)


def _build_knowledge_context(unified: dict) -> str:
    """Build formatted context from unified experience data."""
    sections = []

    # Add summaries
    if unified.get("summaries"):
        sections.append("### Previous Professional Summaries")
        for s in unified["summaries"][:5]:
            sections.append(f"\n**Version: {s.get('version_name') or 'Unnamed'}**")
            sections.append(s.get("content", ""))

    # Add experience bullets grouped by relevance
    if unified.get("experience_bullets"):
        sections.append("\n### Experience Achievements (from all CV versions)")
        sections.append("Select the most relevant achievements that match the job requirements:\n")

        # Group by job title for better organization
        by_title = {}
        for b in unified["experience_bullets"]:
            title = b.get("job_title") or "Other Experience"
            if title not in by_title:
                by_title[title] = []
            by_title[title].append(b)

        for title, bullets in by_title.items():
            sections.append(f"\n**{title}**")
            for b in bullets[:10]:  # Limit bullets per title
                company = f" ({b.get('company_name')})" if b.get("company_name") else ""
                sections.append(f"• {b.get('bullet_text')}{company}")

    # Add skills sections
    if unified.get("skills_sections"):
        sections.append("\n### Technical Skills (consolidated)")
        for s in unified["skills_sections"][:3]:
            sections.append(s.get("content", ""))

    return "\n".join(sections)


def _build_enhanced_system_prompt(job_desc: str, instructions: str, knowledge_context: str) -> str:
    """Build system prompt enhanced for knowledge-based generation."""
    enhanced_instructions = """
## KNOWLEDGE-BASED CV GENERATION MODE

You have access to content from MULTIPLE previous CV versions in the knowledge base.
Your task is to create the OPTIMAL CV by intelligently selecting and combining
the best content that matches the target job description.

### Selection Strategy
1. Analyze the job description for key requirements, skills, and keywords
2. Select achievements and experiences that best demonstrate these requirements
3. Choose the strongest, most impactful bullet points from the available content
4. Combine similar achievements into more powerful statements when appropriate
5. Ensure selected content creates a coherent narrative

### Quality Criteria
- Prioritize quantified achievements with metrics
- Select experiences most relevant to the target role
- Choose content that demonstrates leadership, impact, and results
- Avoid redundancy - pick the single best version of similar achievements
- Maintain chronological and logical consistency
"""
    prompt_parts = [
        CV_OPTIMIZATION_SYSTEM_PROMPT,
        enhanced_instructions,
        CV_FORMAT_REQUIREMENTS,
        "\n## Target Job Description\n",
        job_desc,
    ]

    if instructions and instructions.strip():
        prompt_parts.extend(
            [
                "\n\n## Additional User Instructions\n",
                instructions,
            ]
        )

    return "\n".join(prompt_parts)


def generate_cv_with_knowledge_base(
    cv_content: str, job_desc: str, instructions: str, unified_experience: dict, max_tokens: int = 16384
) -> Tuple[str, str]:
    """
    Generate CV using knowledge base of previous CV versions.

    Args:
        cv_content: Current/base CV content
        job_desc: Target job description
        instructions: User instructions
        unified_experience: Dict with summaries, experience_bullets, skills_sections
        max_tokens: Maximum tokens for generation

    Returns:
        Tuple of (optimized_cv_markdown, response_id)
    """
    try:
        client = get_llm_client()
        knowledge_context = _build_knowledge_context(unified_experience)
        enhanced_prompt = _build_enhanced_system_prompt(job_desc, instructions, knowledge_context)

        user_message = f"""## Current CV (Base Version)
{cv_content}

## Knowledge Base Content (Previous CV Versions)
{knowledge_context}

---

Create an optimized CV by selecting the best content from both the current CV
and the knowledge base that matches the target job description.
Return ONLY the optimized CV in Markdown format.
"""
        response = client.generate(
            system_prompt=enhanced_prompt, user_prompt=user_message, max_tokens=max_tokens
        )
        cleaned_cv = clean_cv_output(response.content)
        return cleaned_cv, response.response_id
    except Exception as e:
        raise Exception(f"CV generation with knowledge base failed: {str(e)}")


async def generate_cv_with_knowledge(
    user_email: str,
    job_desc: str,
    instructions: str = "",
    base_cv_content: Optional[str] = None,
) -> str:
    """
    Generate an optimal CV using content from ALL previous CV versions.

    Args:
        user_email: User's email for retrieving their CV history
        job_desc: The job description to tailor the CV for
        instructions: Optional additional instructions from the user
        base_cv_content: Optional base CV to use as primary structure

    Returns:
        Optimized CV content in Markdown format
    """
    from cv.cv_knowledge_base import get_knowledge_base

    kb = get_knowledge_base()
    unified = await kb.build_unified_experience(user_email)

    if not unified.get("experience_bullets") and not base_cv_content:
        raise ValueError("No CV content available. Please index at least one CV version first.")

    knowledge_context = _build_knowledge_context(unified)

    logger.info(
        f"Building CV with knowledge base: {unified.get('total_bullets', 0)} bullets, "
        f"{unified.get('total_summaries', 0)} summaries"
    )

    enhanced_prompt = _build_enhanced_system_prompt(job_desc, instructions, knowledge_context)

    if base_cv_content:
        user_message = f"""Please create an optimized CV for the job description provided.

## Base CV Structure (use as template)
{base_cv_content}

## Available Content from CV Knowledge Base
{knowledge_context}

---

Instructions:
- Use the Base CV Structure as your template
- Draw the BEST content from the Knowledge Base that matches the job requirements
- Combine and optimize content to create the strongest possible CV
- Do not add any new skills, experiences, or qualifications not present in the sources
- Output ONLY the optimized CV in Markdown format
- No explanations or commentary"""
    else:
        user_message = f"""Please create an optimized CV for the job description provided.

## Available Content from CV Knowledge Base
{knowledge_context}

---

Instructions:
- Create a well-structured CV using the best content from the Knowledge Base
- Select content that best matches the job requirements
- Do not add any new skills, experiences, or qualifications not present in the sources
- Output ONLY the optimized CV in Markdown format
- No explanations or commentary"""

    try:
        client = get_llm_client()
        response = client.generate(
            system_prompt=enhanced_prompt,
            user_prompt=user_message,
            max_tokens=16384,
        )
        return clean_cv_output(response.content)
    except Exception as e:
        raise Exception(f"CV generation with knowledge base failed: {str(e)}")


# Alias for backward compatibility
CVGenerator = CVGeneratorV2
