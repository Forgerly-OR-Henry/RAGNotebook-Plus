"""Prompt templates."""
from agent.prompts.loader import load_prompt
from agent.prompts.registry import PROMPT_FILES

__all__ = ["PROMPT_FILES", "load_prompt"]
