# utils/llm_client.py
"""
Azure OpenAI Responses API Client

Provides stateful conversation support for CV generation and refinement.
Uses the Responses API for multi-turn conversations with automatic context management.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from LLM"""
    content: str
    response_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AzureLLMClient:
    """
    Azure OpenAI client using the Responses API.
    
    Supports:
    - Single-turn completions
    - Multi-turn conversations via response chaining (previous_response_id)
    - Response retrieval for audit/replay
    """
    
    def __init__(self):
        # Get endpoint and extract resource base URL
        endpoint = os.getenv("AZURE_AI_ENDPOINT", "").rstrip("/")
        self.api_key = os.getenv("AZURE_AI_API_KEY")
        self.model = os.getenv("AZURE_DEPLOYMENT")
        
        if not endpoint or not self.api_key:
            raise ValueError("AZURE_AI_ENDPOINT and AZURE_AI_API_KEY must be set")
        
        # Extract base resource URL (remove /openai/deployments/xxx if present)
        if "/openai/deployments" in endpoint:
            resource_base = endpoint.split("/openai/deployments")[0]
        else:
            resource_base = endpoint
        
        # Responses API uses /openai/v1/ base path
        base_url = f"{resource_base}/openai/v1/"
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url,
        )
        
        logger.info(f"Initialized Azure LLM client with Responses API: {base_url}")
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        previous_response_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a response using the Responses API.
        
        Args:
            system_prompt: Instructions for the model
            user_prompt: User input/request
            max_tokens: Maximum output tokens
            previous_response_id: Optional ID to chain with previous response
            
        Returns:
            LLMResponse with content, response_id, and token usage
        """
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=max_tokens,
                previous_response_id=previous_response_id,
            )
            
            # Extract content from response
            content = response.output_text or ""
            
            usage = response.usage
            
            return LLMResponse(
                content=content,
                response_id=response.id,
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    def retrieve_response(self, response_id: str) -> Optional[LLMResponse]:
        """
        Retrieve a previously generated response.
        
        Args:
            response_id: The ID of the response to retrieve
            
        Returns:
            LLMResponse if found, None otherwise
        """
        try:
            response = self.client.responses.retrieve(response_id)
            
            content = response.output_text or ""
            usage = response.usage
            
            return LLMResponse(
                content=content,
                response_id=response.id,
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve response {response_id}: {e}")
            return None
    
    def delete_response(self, response_id: str) -> bool:
        """
        Delete a stored response.
        
        Args:
            response_id: The ID of the response to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            self.client.responses.delete(response_id)
            logger.info(f"Deleted response: {response_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete response {response_id}: {e}")
            return False


# Singleton instance
_client: Optional[AzureLLMClient] = None


def get_llm_client() -> AzureLLMClient:
    """Get or create the singleton LLM client instance."""
    global _client
    if _client is None:
        _client = AzureLLMClient()
    return _client
