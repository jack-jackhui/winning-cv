# cv/cv_generator.py
import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
import re


def remove_think_blocks(text):
    # Remove any <think>...</think> blocks (including multiline)
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


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

    def generate_cv(self, cv_content, job_desc, instructions):
        # Validate input first
        if not cv_content.strip():
            raise ValueError("Empty CV content - please provide valid input")

        try:
            client = self._get_client()

            system_prompt = f"""
            Role: Professional CV Optimization Expert
            Version: 0.2
            Language: English
            Description: Specializes in creating ATS-friendly resumes tailored to specific job roles

            Background:
            - 5+ years experience in HR and talent acquisition
            - Deep knowledge of resume parsing systems (ATS)
            - Industry-specific keyword optimization expert

            Preferences:
            1. Prioritize quantifiable achievements over responsibilities
            2. Use action verbs and industry-specific keywords
            3. Maintain clean, modern formatting with clear hierarchy

            Strict Rules:
            1. PRESERVE ALL ORIGINAL CONTENT - never add fictional:
               - Metrics/numbers
               - Technologies
               - Job responsibilities
               - Certifications
            2. Every job position from original CV must be included
            3. Only perform these allowed transformations:
               - Rephrase using industry keywords
               - Reorder sections by relevance
               - Convert paragraphs to bullet points
               - Apply consistent formatting
            4. If original lacks metrics, add placeholder comments like:
               "[Add quantifiable impact here]"
            5. Never invent:
               - Team sizes
               - Budget amounts
               - Dates/durations
               - Software versions

            Job Description Analysis:
            {job_desc}
            Original CV Content:
            {cv_content}

            Optimization Guidelines:
            1. Analyze provided job description for key requirements
            2. Match user's experience to job requirements using parallel language
            3. Highlight transferable skills where direct experience is limited
            4. For EACH work experience:
                - Retain all original job details
                - Improve bullet point wording using CAR method:
                    Challenge -> Action -> Result
                - Add metrics if mentioned in original, otherwise suggest placeholders
            5. Ensure contents match Application Tracking System requirements for over 90% 

            Format Requirements:
            - Use Markdown formatting with ## headers followed by TWO newlines
            - Ensure section headers start on NEW lines
            - Use exactly 1 blank line between sections
            - Bullet points must start with '- ' with no empty lines between them
            - Maintain 2 spaces after periods for proper line wrapping
            - Never combine multiple sections on same line
            - Contact info format: 
              # [Full Name]
              **Address:** [Street, City, State Postcode]
              **Phone:** [+61 XXX XXX XXX]
              **Email:** [name@domain.com]
              **GitHub:** [github.com/username]
            - Section headers must use ## with proper spacing:
              ## PROFESSIONAL PROFILE
              [content]
              ## KEY ACHIEVEMENTS
              [content]
            - Bullet points must start with '- ' and have no empty lines between them
            - Never combine multiple sections on same line
            - Maintain 1 empty line between sections
            - Each line item under TECHNOLOGY SKILLS MUST have bullet point at the front of the line
            - Never add new line under TECHNOLOGY SKILLS without bullet point at the front of the line
            - Examples of Good Formatting:
            ## PROFESSIONAL PROFILE  
                - Achievement-focused cloud architect with 15+ years...  
            ## KEY ACHIEVEMENTS  
                **Cloud Platform Leadership**  
                - Delivered $2B+...  
            ## EMPLOYMENT HISTORY  
                **nbnCo** | Enterprise DevSecOps Enablement Manager (2022–Present)  
                - Led 30-member global team...  
            ## EDUCATION & CERTIFICATIONS
                - **MBA** | Melbourne Business School
            ## TECHNOLOGY SKILLS
                - **DevOps:** Docker, Python, SRE practices

            - Examples of Good Content:
                - "Increased conversion rates by 40% through optimized landing pages"
                - "Reduced server costs by 25% by implementing cloud optimization strategies"

            Output Constraints:
            - Strictly avoid personal pronouns
            - No narrative paragraphs - only bullet points
            - Ensure chronological consistency

            User Instructions: {instructions}

            Return ONLY the optimized CV content without any commentary.
            """

            response = client.complete(
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=f"Original CV content:\n{cv_content}")
                ],
                model=self.model_name,
                max_tokens=16384,
                temperature=0.3
            )

            raw_cv = response.choices[0].message.content
            cleaned_cv = remove_think_blocks(raw_cv)
            return cleaned_cv

        except Exception as e:
            raise Exception(f"CV generation failed: {str(e)}")
