# cv/cv_generator.py
import logging
import os
import re

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


def remove_think_blocks(text):
    # Remove any <think>...</think> blocks (including multiline)
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def remove_markdown_wrappers(text):
    """Remove markdown code block wrappers (```markdown ... ```) from LLM output"""
    # Remove opening ```markdown or ``` at the start
    text = re.sub(r'^```(?:markdown)?\s*\n?', '', text.strip())
    # Remove closing ``` at the end
    text = re.sub(r'\n?```\s*$', '', text.strip())
    return text.strip()


# Professional CV Optimization System Prompt
CV_OPTIMIZATION_SYSTEM_PROMPT = """
## Role
You are a Professional CV & Resume Optimization Assistant.

## Background
You are a specialized AI assistant focused on resume (CV) creation, optimization, and tailoring for job seekers across industries, functions, and seniority levels. You have deep knowledge of:
- Modern recruitment and hiring practices
- Applicant Tracking Systems (ATS) and keyword parsing
- Recruiter and hiring-manager screening behavior
- Industry-specific resume standards and trends

You understand how resumes are evaluated by both automated systems and human reviewers, and you optimize for both.

## Primary Objective
Your primary objective is to optimize and tailor the user's CV to the provided job description in order to maximize interview chances—without adding or inventing experience.

## Core Responsibilities

### Analyze the job description to identify:
- Core responsibilities
- Required and preferred skills
- Keywords and phrases relevant to ATS and recruiters

### Analyze the user's CV to assess:
- Content quality, clarity, and structure
- Keyword coverage
- Relevance and transferability of experience

### Align the CV to the job description by:
- Repositioning existing experience to emphasize relevance
- Highlighting transferable skills
- Optimizing keywords using the user's existing content only
- Improve readability and impact while maintaining ATS compatibility

## Guiding Principles
- Be concise, structured, and results-oriented
- Emphasize practical experience and measurable outcomes
- Focus on transferable skills, especially for role or industry transitions
- Prioritize clarity, scannability, and relevance
- Use strong action verbs and well-structured bullet points
- Never assume, exaggerate, or fabricate experience

## Strict Constraints (MUST Follow)
1. All edits and suggestions must be strictly based on the content provided in the user's CV
2. You may rewrite, reorder, condense, or emphasize content—but must NOT add:
   - New responsibilities
   - New skills, tools, technologies, or certifications
   - New achievements, metrics, or qualifications
3. All recommendations must reflect current industry standards and recruitment trends
4. Guidance must be clear, practical, and easy to apply
5. Maintain complete factual accuracy at all times

## Capabilities & Expertise
- Resume rewriting and restructuring
- ATS-optimized keyword alignment
- Job-description-driven tailoring
- Industry- and role-specific optimization
- Bullet-point rewriting using impact-focused / STAR-style framing
- Identification and strategic positioning of transferable skills

## Preferred Resume Style
- Clean, professional, modern layout
- Clear section hierarchy (Summary, Experience, Skills, Education, etc.)
- Bullet points limited to 1-2 lines where possible
- Outcome-oriented phrasing
- Keyword usage aligned with job description terminology

## Required Workflow
For every request, follow this process:
1. Extract key requirements and keywords from the job description
2. Evaluate alignment between the CV and the job description
3. Rewrite or suggest edits to improve relevance and clarity
4. Explicitly map CV content to job requirements
5. Ensure contents match Application Tracking System requirements for over 90%

## Mandatory Job Description Alignment
You must always:
- Treat the job description as the primary optimization target
- Use job-specific language and keywords where they naturally match the CV
- Highlight transferable skills that satisfy job requirements
- Identify implicit matches (e.g., similar responsibilities phrased differently)
- Never introduce experience that is not already present in the CV

**Reminder: Your role is to optimize positioning, not create new qualifications.**
"""

# Format requirements for consistent CV output - matches source CV style
CV_FORMAT_REQUIREMENTS = """
## Output Format Requirements

CRITICAL: You MUST preserve the EXACT formatting style from the original CV provided.
Analyze the original CV's structure and replicate it precisely.

### Header Format (Single Line Contact)
The name and contact info should be on a SINGLE LINE with pipe separators:
```
# FULL NAME IN UPPERCASE
+61 XXX XXX XXX | email@domain.com | City, State, Country | github.com/username
```

### Section Headers Format
Section headers must use ## with UPPERCASE text:
```
## EXECUTIVE PROFILE
[paragraph content - NOT bullet points for profile summary]

## CORE STRENGTHS
[bullet points with • character]

## CAREER HIGHLIGHTS
[bullet points with • character]

## PROFESSIONAL EXPERIENCE
**Company Name** | Role Title | Location | Dates
[bullet points describing responsibilities and achievements]

## EDUCATION & CERTIFICATIONS
[bullet points]

## TECHNOLOGY SKILLS
[bullet points with category: items format]
```

### Formatting Rules
- Use • (bullet character) for all bullet points, NOT - (dash)
- Profile/Summary sections should be flowing paragraphs, NOT bullet points
- Keep content COMPACT - minimize whitespace
- Employment entries: **Company** | Role | Location | Dates (all on one line)
- Bullet points should be concise, achievement-focused
- Use pipe | as separator in contact line and employment headers

### Example of Correct Formatting
```
# JOHN SMITH
+61 400 123 456 | john@email.com | Melbourne, VIC, AU | linkedin.com/in/johnsmith

## EXECUTIVE PROFILE
Strategic technology leader with 15+ years delivering enterprise-scale digital transformation. Proven track record driving AI adoption and platform modernisation across financial services and telecommunications.

## CORE STRENGTHS
• Enterprise AI strategy and roadmap ownership
• Executive engagement and stakeholder alignment
• Governance and compliance frameworks

## PROFESSIONAL EXPERIENCE
**Company Name** | Chief Technology Officer | Melbourne, VIC | 2020–Present
• Led digital transformation program delivering $50M annual savings
• Established AI governance framework adopted across organisation

## EDUCATION & CERTIFICATIONS
• **MBA** | Melbourne Business School | 2015
• AWS Solutions Architect Professional

## TECHNOLOGY SKILLS
• **Cloud Platforms:** AWS, Azure, GCP
• **AI/ML:** TensorFlow, PyTorch, LangChain
• **Languages:** Python, Go, TypeScript
```

### Content Guidelines
- Strictly avoid personal pronouns (I, my, we)
- Executive Profile should be 2-3 sentences, NOT bullet points
- Core Strengths: 4-6 bullet points maximum
- Use action verbs and quantified achievements
- Ensure chronological consistency (most recent first)

### Final Output
Return ONLY the optimized CV content in Markdown format.
Do NOT include any commentary, explanations, or rationale.
Do NOT include the job description in the output.
"""


class CVGenerator:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_AI_ENDPOINT")
        self.key = os.getenv("AZURE_AI_API_KEY")
        self.model_name = os.getenv("AZURE_DEPLOYMENT")

    def _get_client(self):
        return ChatCompletionsClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.key)
        )

    def _build_system_prompt(self, job_desc: str, instructions: str) -> str:
        """Build the complete system prompt with job description and user instructions."""
        prompt_parts = [
            CV_OPTIMIZATION_SYSTEM_PROMPT,
            CV_FORMAT_REQUIREMENTS,
            "\n## Job Description to Optimize For\n",
            job_desc,
        ]

        if instructions and instructions.strip():
            prompt_parts.extend([
                "\n\n## Additional User Instructions\n",
                instructions,
            ])

        return "\n".join(prompt_parts)

    def generate_cv(self, cv_content: str, job_desc: str, instructions: str) -> str:
        """
        Generate a tailored CV based on the original CV and job description.

        Args:
            cv_content: The user's original CV content
            job_desc: The job description to tailor the CV for
            instructions: Optional additional instructions from the user

        Returns:
            Optimized CV content in Markdown format

        Raises:
            ValueError: If CV content is empty
            Exception: If CV generation fails
        """
        # Validate input first
        if not cv_content.strip():
            raise ValueError("Empty CV content - please provide valid input")

        try:
            client = self._get_client()

            system_prompt = self._build_system_prompt(job_desc, instructions)

            user_message = f"""Please optimize the following CV for the job description provided in the system prompt.

## Original CV Content

{cv_content}

---

Remember:
- Only use content from the original CV above
- Do not add any new skills, experiences, or qualifications
- Output ONLY the optimized CV in Markdown format
- No explanations or commentary"""

            response = client.complete(
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=user_message)
                ],
                model=self.model_name,
                # Note: temperature not supported by reasoning models (o1, o3-mini)
                model_extras={"max_completion_tokens": 16384}
            )

            raw_cv = response.choices[0].message.content
            cleaned_cv = remove_think_blocks(raw_cv)
            cleaned_cv = remove_markdown_wrappers(cleaned_cv)
            return cleaned_cv

        except Exception as e:
            raise Exception(f"CV generation failed: {str(e)}")


async def generate_cv_with_knowledge(
    user_email: str,
    job_desc: str,
    instructions: str = "",
    base_cv_content: str = None,
) -> str:
    """
    Generate an optimal CV using content from ALL previous CV versions.

    This function retrieves all indexed CV content from the knowledge base
    and uses it to create the best possible CV for the given job description.

    Args:
        user_email: User's email for retrieving their CV history
        job_desc: The job description to tailor the CV for
        instructions: Optional additional instructions from the user
        base_cv_content: Optional base CV to use as primary structure

    Returns:
        Optimized CV content in Markdown format

    Raises:
        ValueError: If no CV content is available
        Exception: If CV generation fails
    """
    from cv.cv_knowledge_base import get_knowledge_base

    kb = get_knowledge_base()

    # Get unified experience from all CV versions
    unified = await kb.build_unified_experience(user_email)

    if not unified['experience_bullets'] and not base_cv_content:
        raise ValueError(
            "No CV content available. Please index at least one CV version first."
        )

    # Build comprehensive CV content from knowledge base
    knowledge_context = _build_knowledge_context(unified)

    logger.info(
        f"Building CV with knowledge base: {unified['total_bullets']} bullets, "
        f"{unified['total_summaries']} summaries"
    )

    # Generate CV with enhanced context
    generator = CVGenerator()

    # Build enhanced system prompt
    enhanced_prompt = _build_enhanced_system_prompt(
        job_desc, instructions, knowledge_context
    )

    # Prepare user message
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
        client = generator._get_client()

        response = client.complete(
            messages=[
                SystemMessage(content=enhanced_prompt),
                UserMessage(content=user_message)
            ],
            model=generator.model_name,
            model_extras={"max_completion_tokens": 16384}
        )

        raw_cv = response.choices[0].message.content
        cleaned_cv = remove_think_blocks(raw_cv)
        cleaned_cv = remove_markdown_wrappers(cleaned_cv)
        return cleaned_cv

    except Exception as e:
        raise Exception(f"CV generation with knowledge base failed: {str(e)}")


def _build_knowledge_context(unified: dict) -> str:
    """Build formatted context from unified experience data."""
    sections = []

    # Add summaries
    if unified['summaries']:
        sections.append("### Previous Professional Summaries")
        for i, s in enumerate(unified['summaries'][:5], 1):
            sections.append(f"\n**Version: {s['version_name'] or 'Unnamed'}**")
            sections.append(s['content'])

    # Add experience bullets grouped by relevance
    if unified['experience_bullets']:
        sections.append("\n### Experience Achievements (from all CV versions)")
        sections.append(
            "Select the most relevant achievements that match the job requirements:\n"
        )

        # Group by job title for better organization
        by_title = {}
        for b in unified['experience_bullets']:
            title = b['job_title'] or 'Other Experience'
            if title not in by_title:
                by_title[title] = []
            by_title[title].append(b)

        for title, bullets in by_title.items():
            sections.append(f"\n**{title}**")
            for b in bullets[:10]:  # Limit bullets per title
                company = f" ({b['company_name']})" if b['company_name'] else ""
                sections.append(f"• {b['bullet_text']}{company}")

    # Add skills sections
    if unified['skills_sections']:
        sections.append("\n### Technical Skills (consolidated)")
        for s in unified['skills_sections'][:3]:
            sections.append(s['content'])

    return "\n".join(sections)


def _build_enhanced_system_prompt(
    job_desc: str,
    instructions: str,
    knowledge_context: str
) -> str:
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
        prompt_parts.extend([
            "\n\n## Additional User Instructions\n",
            instructions,
        ])

    return "\n".join(prompt_parts)
