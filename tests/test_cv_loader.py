import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.cv_loader import load_cv_content


def test_cv_loading():
    print("Testing CV loader...")

    # Test default path
    print("\nTest 1: Default path")
    print(load_cv_content())

    # Test absolute path
    print("\nTest 2: Absolute path")
    abs_path = os.path.abspath("user_cv/CV_Jack_HUI_08042025_EL.docx")
    print(load_cv_content(abs_path))

    # Test invalid file
    print("\nTest 3: Invalid file")
    print(load_cv_content("user_cv/invalid.docx"))


if __name__ == "__main__":
    test_cv_loading()
