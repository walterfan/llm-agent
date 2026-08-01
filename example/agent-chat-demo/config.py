"""Configuration for agent chat demo."""

import os

# LLM settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# Conversation limits
MAX_TURNS_PER_AGENT = 10
MAX_TOTAL_TURNS = 20
TOKEN_BUDGET = 4000
SIMILARITY_THRESHOLD = 0.85
MAX_CONSECUTIVE_AGENT_MSGS = 6
TIMEOUT_SECONDS = 300
