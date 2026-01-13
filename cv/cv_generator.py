# cv/cv_generator.py
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
import re


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
