"""
Sample queries and optional fallback documentation corpus for ContextIQ.
"""

SAMPLE_QUERIES = [
    "Where is the auth token generated?",
    "What environment variables are required for authentication?",
    "How do I connect to the database?",
    "Which endpoint lists all users?",
    "What does the /api/projects/<project_id> route return?",
    "Is there any mention of payment processing in these docs?",
    "How does a client refresh an access token?",
    "Which fields are stored in the users table?",
]

# Fallback corpus used if the docs/ directory is missing or empty.
FALLBACK_DOCS = {
    "AUTH.md": """
# Authentication Guide

Tokens are created by the generate_access_token function inside auth_utils.py.
They are signed using the AUTH_SECRET_KEY environment variable.

Clients authenticate by sending a POST request to /api/login. They receive
a token which must be included in the Authorization header for all future
requests.

A token can be refreshed using POST /api/refresh.
""",
    "API_REFERENCE.md": """
# API Reference

GET /api/users returns all users. Requires a valid Authorization token.
GET /api/users/<user_id> returns data for a specific user.
GET /api/projects/<project_id> returns detailed project info.

POST /api/login validates credentials and returns an access token.
""",
    "DATABASE.md": """
# Database Guide

The users table contains:
- user_id
- email
- password_hash
- joined_at

The projects table contains:
- project_id
- name
- description
- status
- owner_id
""",
    "SETUP.md": """
# Setup Guide

Set DATABASE_URL and AUTH_SECRET_KEY before running the application.
Install dependencies with pip install -r requirements.txt.
Run the server using python app.py.
""",
}


def load_fallback_documents():
    """Returns FALLBACK_DOCS as a list of (filename, text) tuples."""
    return list(FALLBACK_DOCS.items())
