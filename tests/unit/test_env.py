import os
from dotenv import load_dotenv
import pytest
import sys

def verify_environment():
    """Verify that all required environment variables are present and loaded correctly."""
    # Load environment variables from .env file
    load_dotenv()

    # Required environment variables grouped by category
    required_vars = {
        'Gemini API Keys': [
            'GEMINI_API_KEY_OCR',
            'GEMINI_API_KEY_RECOMMENDATION',
            'GEMINI_API_KEY_SENTIMENT',
            'GEMINI_API_KEY_CHATBOT',
            'ORCHESTRATOR_API_KEY',
            'TASK_DECOMPOSER_API_KEY',
            'RESULT_VERIFIER_API_KEY'
        ],
        'Database Configuration': [
            'MONGODB_URI',
            'VECTOR_DB_PATH'
        ],
        'API Configuration': [
            'API_HOST',
            'API_PORT',
            'API_DEBUG'
        ],
        'Security': [
            'JWT_SECRET_KEY',
            'JWT_ALGORITHM',
            'ACCESS_TOKEN_EXPIRE_MINUTES'
        ]
    }

    # Check each category of variables
    missing_vars = {}
    for category, vars in required_vars.items():
        category_missing = []
        for var in vars:
            if not os.getenv(var):
                category_missing.append(var)
        if category_missing:
            missing_vars[category] = category_missing

    # If any variables are missing, raise an error with detailed information
    if missing_vars:
        error_message = "Missing required environment variables:\n"
        for category, vars in missing_vars.items():
            error_message += f"\n{category}:\n"
            for var in vars:
                error_message += f"  - {var}\n"
        return False, error_message
    
    return True, "Environment setup successfully! All required variables are present."

def test_environment_variables():
    """Test function for pytest to verify environment variables."""
    success, message = verify_environment()
    if not success:
        pytest.fail(message)
    assert success, message

if __name__ == '__main__':
    # When run directly, provide a user-friendly output
    success, message = verify_environment()
    if success:
        print("\033[92m✅ " + message + "\033[0m")  # Green color for success
        sys.exit(0)
    else:
        print("\033[91m❌ Error: " + message + "\033[0m")  # Red color for error
        sys.exit(1) 