"""
Security checks for prompt injection and PII detection.
"""
import hashlib
import re
from typing import Any, Dict, Tuple

# Common prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    r'(?i)(ignore|forget|disregard).*previous.*instructions?',
    r'(?i)(system|assistant|you are).*now.*',
    r'(?i)(new instructions?|override|replace)',
    r'(?i)(act as|pretend to be|you must)',
    r'(?i)(tell me|reveal|show me).*(password|api.?key|secret|token)',
    r'(?i)(repeat|echo|output).*(the|all|every).*(word|character)',
    r'(?i)(delete|remove|clear).*(all|everything|data)',
    r'<\|.*\|>',  # Special tokens
    r'\[.*system.*\]',  # System-like markers
]

# PII patterns (simplified regex-based detection)
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
    'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
    'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
}


def hash_prompt(prompt: str) -> str:
    """Generate SHA256 hash of prompt."""
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()


def redact_preview(prompt: str, max_length: int = 50) -> str:
    """Create a redacted preview of the prompt."""
    if len(prompt) <= max_length:
        return prompt
    
    # Show first 20 chars and last 20 chars
    preview = prompt[:20] + '...' + prompt[-20:]
    return preview


def check_prompt_injection(prompt: str) -> bool:
    """
    Check for prompt injection patterns.
    
    Returns:
        True if potential injection detected, False otherwise.
    """
    prompt_lower = prompt.lower()
    
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return True
    
    return False


def detect_pii(prompt: str) -> Dict[str, int]:
    """
    Detect PII in the prompt.
    
    Returns:
        Dictionary mapping PII type to count of detections.
    """
    detections = {}
    
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        if matches:
            detections[pii_type] = len(matches)
    
    return detections


def analyze_security(prompt: str) -> Dict[str, Any]:
    """
    Perform comprehensive security analysis on the prompt.
    
    Returns:
        Dictionary with security analysis results:
        - prompt_injection: bool
        - pii_detected: bool
        - pii_types: dict
        - prompt_hash: str
        - prompt_preview: str
    """
    prompt_injection = check_prompt_injection(prompt)
    pii_types = detect_pii(prompt)
    pii_detected = len(pii_types) > 0
    
    return {
        'prompt_injection': prompt_injection,
        'pii_detected': pii_detected,
        'pii_types': pii_types,
        'prompt_hash': hash_prompt(prompt),
        'prompt_preview': redact_preview(prompt),
    }

