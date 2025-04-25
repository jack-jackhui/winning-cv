from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import re
import json
import logging
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
from config.settings import Config
from tenacity import retry, stop_after_attempt, wait_exponential


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
                temperature=0.2,
                max_tokens=2000
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

    def calculate_match_score(self, job_desc, cv_text, use_llm=True, weights=None):
        """
        Fixed scoring logic:
        - Always calculates TF-IDF first
        - Conditionally adds LLM analysis
        """
        tfidf_score = self.basic_match_score(job_desc, cv_text)
        default_result = {
            'score': tfidf_score,
            'reasons': [],
            'suggestions': []
        }

        if not use_llm:
            return tfidf_score, None

        try:
            llm_result = self._llm_evaluation(job_desc, cv_text)
            self.logger.debug(f"LLM evaluation result: {llm_result}")
            if llm_result:
                final_score = (tfidf_score * 0.1) + (llm_result['score'] * 0.9)
                return final_score, llm_result

            self.logger.warning("LLM returned no result, using TF-IDF only")
            return tfidf_score, default_result

        except Exception as e:
            self.logger.warning(f"LLM scoring failed, using TF-IDF only: {str(e)}")
            return tfidf_score, default_result

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

