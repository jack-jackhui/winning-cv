import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.matcher import JobMatcher
from utils.logger import setup_logger


def test_llm_response():
    setup_logger()
    matcher = JobMatcher()

    test_job = "Software engineer position requiring Python and cloud experience"
    test_cv = "Experienced Python developer with AWS expertise and machine learning skills"

    print("Testing LLM evaluation...")
    result = matcher._llm_evaluation(test_job, test_cv)
    print(f"LLM result: {result}")


if __name__ == "__main__":
    test_llm_response()
