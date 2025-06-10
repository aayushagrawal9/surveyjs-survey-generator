"""Gemini API client and caching functionality."""

import logging
from pathlib import Path
from typing import List, Optional
from joblib import Memory, expires_after
from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse

from ..config.settings import settings

logger = logging.getLogger(__name__)

# Initialize joblib Memory and Gemini client
memory = Memory(settings.CACHE_DIR, verbose=0)
client = genai.Client(api_key=settings.GEMINI_API_KEY)


@memory.cache(cache_validation_callback=expires_after(hours=settings.FILE_UPLOAD_TTL_HOURS))
def upload_file_to_gemini(file: Path, mime_type: str):
    """Upload file to Gemini with caching."""
    logger.debug(f"Uploading file to Gemini: {file.name}, {mime_type}")
    return client.files.upload(file=file, config=types.UploadFileConfig(mime_type=mime_type))


@memory.cache()  # No TTL for call_gemini cache
def call_gemini(
    system_instruction: str, 
    model: str = settings.DEFAULT_MODEL,
    contents: Optional[List[types.Content]] = None,
    response_mime_type: str = "application/json",
    call_name: str = "API Call",
    cached_content: Optional[str] = None
) -> GenerateContentResponse:
    """Call Gemini API with optional cached content support."""
    if contents is None:
        contents = []
        
    config = types.GenerateContentConfig(
        response_mime_type=response_mime_type, 
        temperature=0.0, 
        automatic_function_calling={'disable': True}
    )
    
    # Add cached content if provided, otherwise use system instruction
    if cached_content:
        config.cached_content = cached_content
        # Note: system_instruction must be in cached content when using cache
    else:
        config.system_instruction = system_instruction
    
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config
    )
    
    # Log usage data immediately after API call
    usage = response.usage_metadata if hasattr(response, 'usage_metadata') else None
    if usage:
        logger.info(f"✓ {call_name} completed:")
        logger.info(f"  • Prompt tokens:      {getattr(usage, 'prompt_token_count', 0):,}")
        candidates_tokens = getattr(usage, 'candidates_token_count', None)
        candidates_tokens = candidates_tokens if candidates_tokens is not None else 0
        logger.info(f"  • Candidates tokens:  {candidates_tokens:,}")
        logger.info(f"  • Total tokens:       {getattr(usage, 'total_token_count', 0):,}")
        cached_tokens = getattr(usage, 'cached_content_token_count', None)
        if cached_tokens is not None and cached_tokens > 0:
            logger.info(f"  • Cached tokens:      {cached_tokens:,}")
    else:
        logger.info(f"✓ {call_name} completed (usage data unavailable)")
    
    return response


@memory.cache(cache_validation_callback=expires_after(minutes=settings.EXAMPLES_CACHE_TTL_MINUTES))
def create_examples_cache(
    examples_content: str, 
    model: str = settings.DEFAULT_MODEL, 
    system_instruction: Optional[str] = None
) -> Optional[str]:
    """Create a Google Gemini context cache for examples with TTL."""
    if not examples_content:
        return None
    
    logger.info(f"Creating context cache for examples ({settings.EXAMPLES_CACHE_TTL_MINUTES} min TTL)")
    
    # Create cache with TTL and system instruction
    cache_config = types.CreateCachedContentConfig(
        contents=[types.Content(
            role="user",
            parts=[types.Part.from_text(text=examples_content)]
        )],
        ttl=f"{settings.EXAMPLES_CACHE_TTL_MINUTES * 60}s",  # Convert minutes to seconds
        display_name="Survey Examples Cache"
    )
    
    # Add system instruction to cache if provided
    if system_instruction:
        cache_config.system_instruction = system_instruction
    
    cache = client.caches.create(
        model=model,
        config=cache_config
    )
    
    logger.info(f"Created context cache: {cache.name}")
    return cache.name