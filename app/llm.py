"""
Gemini Vertex AI integration for LLM requests.
"""
import os
import time
from typing import Dict, Optional, Tuple

import logging

import vertexai
from vertexai.generative_models import GenerativeModel

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Gemini on Vertex AI."""
    
    def __init__(self):
        """Initialize the Gemini client with Vertex AI configuration."""
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('VERTEX_LOCATION', 'us-central1')
        model_name = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro')
        
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        self.model_name = model_name
        self.project_id = project_id
        self.location = location
        
        logger.info(
            "Gemini client initialized",
            extra={
                "project_id": project_id,
                "location": location,
                "model": model_name
            }
        )
    
    def generate(self, prompt: str, request_id: str) -> Tuple[str, Dict[str, int], float]:
        """
        Generate a response using Gemini.
        
        Args:
            prompt: The input prompt
            request_id: Unique request identifier
            
        Returns:
            Tuple of (response_text, token_counts, latency_ms)
            token_counts: dict with 'tokens_in' and 'tokens_out' keys
        """
        start_time = time.time()
        
        try:
            model = GenerativeModel(self.model_name)
            
            # Generate content
            response = model.generate_content(prompt)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response text
            response_text = response.text if response.text else ""
            
            # Extract token counts if available
            token_counts = {
                'tokens_in': 0,
                'tokens_out': 0,
            }
            
            # Try to get token counts from response
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                # Try different attribute names for token counts
                if hasattr(usage, 'prompt_token_count'):
                    token_counts['tokens_in'] = usage.prompt_token_count
                elif hasattr(usage, 'prompt_token_counts'):
                    # Sum all prompt token counts if it's a list
                    if isinstance(usage.prompt_token_counts, list):
                        token_counts['tokens_in'] = sum(usage.prompt_token_counts)
                    else:
                        token_counts['tokens_in'] = usage.prompt_token_counts
                
                if hasattr(usage, 'candidates_token_count'):
                    token_counts['tokens_out'] = usage.candidates_token_count
                elif hasattr(usage, 'candidates_token_counts'):
                    if isinstance(usage.candidates_token_counts, list):
                        token_counts['tokens_out'] = sum(usage.candidates_token_counts)
                    else:
                        token_counts['tokens_out'] = usage.candidates_token_counts
                elif hasattr(usage, 'total_token_count'):
                    # Fallback: try to estimate from total
                    token_counts['tokens_out'] = max(0, usage.total_token_count - token_counts['tokens_in'])
            
            logger.info(
                "LLM request completed",
                extra={
                    "request_id": request_id,
                    "model": self.model_name,
                    "latency_ms": latency_ms,
                    "tokens_in": token_counts['tokens_in'],
                    "tokens_out": token_counts['tokens_out'],
                }
            )
            
            return response_text, token_counts, latency_ms
            
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "LLM request failed",
                extra={
                    "request_id": request_id,
                    "model": self.model_name,
                    "latency_ms": latency_ms,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise

