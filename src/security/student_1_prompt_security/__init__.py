"""Security package for the InvestSage Agentic AI system.

Provides prompt-injection and jailbreak defense across 6 evaluation areas:
1. Prompt Injection
2. Jailbreak Attempts
3. Prompt Leakage
4. Instruction Override
5. Prompt Manipulation
6. Prompt Robustness
"""
from .attack_detector import AttackFinding, PromptAttackDetector
from .prompt_security import (
    PromptSecurityGateway,
    REFUSAL_MESSAGE,
    ROBUSTNESS_MESSAGE,
    redact_sensitive_text,
)
from .evaluator import (
    evaluate_cases,
    evaluate_directory,
    print_evaluation_report,
    save_report,
)

__all__ = [
    "AttackFinding",
    "PromptAttackDetector",
    "PromptSecurityGateway",
    "REFUSAL_MESSAGE",
    "ROBUSTNESS_MESSAGE",
    "redact_sensitive_text",
    "evaluate_cases",
    "evaluate_directory",
    "print_evaluation_report",
    "save_report",
]