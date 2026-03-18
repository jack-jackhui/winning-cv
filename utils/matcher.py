import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

import spacy
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import Config
from utils.ats_scorer import score_resume_ats
from utils.hr_scorer import score_resume_hr


class JobMatcher:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.llm_client = self._init_azure_llm()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _init_azure_llm(self):
        """Initialize Azure LLM client using centralized config"""
        return ChatCompletionsClient(
            endpoint=Config.AZURE_AI_ENDPOINT,
            credential=AzureKeyCredential(Config.AZURE_AI_API_KEY),
        )

    def _llm_evaluation(self, job_desc, cv_text):
        """Use Azure LLM for advanced matching evaluation"""
        if not job_desc.strip() or not cv_text.strip():
            self.logger.warning("Empty input for LLM evaluation")
            return None

        system_prompt = """You are an expert recruiter. Analyze the match between a CV and job description.
        Consider skills, experience, qualifications, and cultural fit. Return a JSON response with:
        - score (0-10)
        - reasons (list of key matching factors)
        - improvement_suggestions (list of areas to improve)
        Your response MUST be valid JSON with only these keys. Format:
        {
        "score": 7.5,
        "reasons": ["Relevant experience", "Matching skills"],
        "improvement_suggestions": ["Add more keywords", "Highlight leadership experience"]
        }
        """

        user_prompt = f"""
        Job Description:
        {job_desc}

        CV Text:
        {cv_text}

        Provide your analysis:
        """

        try:
            response = self.llm_client.complete(
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=user_prompt)
                ],
                model=Config.AZURE_DEPLOYMENT,
                # Note: temperature not supported by reasoning models (o1, o3-mini)
                model_extras={"max_completion_tokens": 2000}
            )

            # Add response validation
            if not response.choices:
                self.logger.error("Empty response from LLM API")
                return None

            if not response.choices[0].message.content:
                self.logger.error("Empty content in LLM response")
                return None

            # Add raw response logging
            # raw_response = response.choices[0].message.content
            # self.logger.debug(f"Raw LLM response: {raw_response}")

            return self._parse_llm_response(response.choices[0].message.content)

        except Exception as e:
            self.logger.error(f"LLM evaluation failed: {str(e)}")
            return None

    def _parse_llm_response(self, response_text):
        """Parse LLM JSON response with enhanced error handling"""
        try:
            # First try direct parse
            response = json.loads(response_text)
            self.logger.debug("Initial JSON parse successful")
        except json.JSONDecodeError:
            self.logger.warning("Initial JSON parse failed, attempting extraction")
            try:
                # Try to extract JSON from markdown code blocks
                clean_text = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
                if clean_text:
                    response = json.loads(clean_text.group(1))
                    self.logger.debug("Extracted JSON from code block")
                else:
                    # Try to find any JSON structure
                    clean_text = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if not clean_text:
                        raise ValueError("No JSON structure found")
                    response = json.loads(clean_text.group())
                    self.logger.debug("Extracted JSON from text")
            except Exception as e:
                self.logger.error(f"JSON extraction failed: {str(e)}")
                self.logger.debug(f"Problematic response text: {response_text[:500]}")  # Log first 500 chars
                return None

        try:
            # Validate required fields
            if 'score' not in response:
                raise ValueError("Missing 'score' field in response")

            return {
                'score': min(max(float(response['score']), 0), 10),
                'reasons': response.get('reasons', []),
                'suggestions': response.get('improvement_suggestions', [])
            }
        except KeyError as e:
            self.logger.error(f"Missing required key in response: {str(e)}")
            self.logger.debug(f"Partial response: {response}")
            return None
        except Exception as e:
            self.logger.error(f"Response validation failed: {str(e)}")
            return None

    def preprocess_text(self, text):
        """Clean and lemmatize text"""
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
        doc = self.nlp(text)
        return ' '.join([token.lemma_ for token in doc if not token.is_stop])

    def calculate_match_score(
        self,
        job_desc: str,
        cv_text: str,
        use_llm: bool = True,
        weights: Optional[Dict[str, float]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate comprehensive match score using ATS, HR, and optionally LLM evaluation.

        Args:
            job_desc: Job description text
            cv_text: CV/resume text
            use_llm: Whether to include LLM evaluation (expensive, optional)
            weights: Optional custom weights. Defaults:
                     - With LLM: ATS(25%) + HR(35%) + LLM(40%)
                     - Without LLM: ATS(40%) + HR(60%)

        Returns:
            Tuple of (overall_score on 0-10 scale, analysis_dict)
        """
        # Run ATS and HR scorers (rule-based, fast)
        ats_result = self._safe_ats_score(job_desc, cv_text)
        hr_result = self._safe_hr_score(job_desc, cv_text)

        # Extract scores (0-100 scale from scorers)
        ats_score = ats_result.get('total_score', 0) if ats_result else 0
        hr_score = hr_result.get('overall_score', 0) if hr_result else 0

        # Build analysis result
        analysis = {
            'ats_score': round(ats_score, 1),
            'hr_score': round(hr_score, 1),
            'llm_score': None,
            'ats_breakdown': ats_result,
            'hr_breakdown': hr_result,
            'recommendation': hr_result.get('recommendation') if hr_result else None,
            'reasons': [],
            'suggestions': []
        }

        # Collect reasons and suggestions from HR scorer
        if hr_result:
            analysis['reasons'] = hr_result.get('strengths', [])
            analysis['suggestions'] = hr_result.get('concerns', [])

        # Add keyword info from ATS
        if ats_result:
            matched_kw = ats_result.get('matched_keywords', [])
            missing_kw = ats_result.get('missing_keywords', [])
            if matched_kw:
                analysis['reasons'].insert(0, f"Matched keywords: {', '.join(matched_kw[:5])}")
            if missing_kw:
                analysis['suggestions'].append(f"Missing keywords: {', '.join(missing_kw[:5])}")

        llm_score = None
        if use_llm:
            try:
                llm_result = self._llm_evaluation(job_desc, cv_text)
                if llm_result:
                    llm_score = llm_result.get('score', 0)  # 0-10 scale
                    analysis['llm_score'] = round(llm_score, 1)
                    # Merge LLM reasons/suggestions
                    if llm_result.get('reasons'):
                        analysis['reasons'].extend(llm_result['reasons'])
                    if llm_result.get('suggestions'):
                        analysis['suggestions'].extend(llm_result['suggestions'])
                    self.logger.debug(f"LLM evaluation: score={llm_score}")
            except Exception as e:
                self.logger.warning(f"LLM evaluation failed, continuing without: {e}")

        # Calculate overall score
        # Convert ATS and HR from 0-100 to 0-10 scale for consistency
        ats_normalized = ats_score / 10
        hr_normalized = hr_score / 10

        if llm_score is not None:
            # With LLM: ATS(25%) + HR(35%) + LLM(40%)
            w = weights or {'ats': 0.25, 'hr': 0.35, 'llm': 0.40}
            overall_score = (
                ats_normalized * w.get('ats', 0.25) +
                hr_normalized * w.get('hr', 0.35) +
                llm_score * w.get('llm', 0.40)
            )
        else:
            # Without LLM: ATS(40%) + HR(60%)
            w = weights or {'ats': 0.40, 'hr': 0.60}
            overall_score = (
                ats_normalized * w.get('ats', 0.40) +
                hr_normalized * w.get('hr', 0.60)
            )

        overall_score = round(max(0, min(10, overall_score)), 2)
        analysis['overall_score'] = overall_score

        # De-duplicate reasons and suggestions
        analysis['reasons'] = list(dict.fromkeys(analysis['reasons']))[:10]
        analysis['suggestions'] = list(dict.fromkeys(analysis['suggestions']))[:10]

        return overall_score, analysis

    def _safe_ats_score(self, job_desc: str, cv_text: str) -> Optional[Dict[str, Any]]:
        """Safely run ATS scorer with error handling."""
        try:
            return score_resume_ats(cv_text, job_desc)
        except Exception as e:
            self.logger.error(f"ATS scoring failed: {e}")
            return None

    def _safe_hr_score(self, job_desc: str, cv_text: str) -> Optional[Dict[str, Any]]:
        """Safely run HR scorer with error handling."""
        try:
            return score_resume_hr(cv_text, job_desc)
        except Exception as e:
            self.logger.error(f"HR scoring failed: {e}")
            return None

    def basic_match_score(self, job_desc, cv_text):
        """TF-IDF scoring without LLM"""
        try:
            clean_job = self.preprocess_text(job_desc)
            clean_cv = self.preprocess_text(cv_text)

            if not clean_job or not clean_cv:
                return 0

            tfidf_matrix = self.vectorizer.fit_transform([clean_job, clean_cv])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return round(similarity * 10, 2)

        except Exception as e:
            self.logger.error(f"TF-IDF scoring failed: {str(e)}")
            return 0

