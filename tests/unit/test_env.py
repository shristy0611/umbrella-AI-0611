import os
from dotenv import load_dotenv
import pytest

def test_environment_variables():
    """Test that all required environment variables are loaded correctly."""
    # Load environment variables from .env file
    load_dotenv()

    # Required Gemini API Keys
    required_vars = [
        'GEMINI_API_KEY_OCR',
        'GEMINI_API_KEY_RECOMMENDATION',
        'GEMINI_API_KEY_SENTIMENT',
        'GEMINI_API_KEY_CHATBOT',
        'ORCHESTRATOR_API_KEY',
        'TASK_DECOMPOSER_API_KEY',
        'RESULT_VERIFIER_API_KEY'
    ]

    # Check each required variable
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    # If any variables are missing, raise an error
    if missing_vars:
        pytest.fail(f"Missing required environment variables: {', '.join(missing_vars)}")

if __name__ == '__main__':
    try:
        test_environment_variables()
        print("✅ Environment variables loaded successfully!")
    except Exception as e:
        print(f"❌ Error: {str(e)}") 