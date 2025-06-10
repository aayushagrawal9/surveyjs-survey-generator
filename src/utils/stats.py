"""Statistics and logging utilities."""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def log_statistics_summary(response_1, response_2, selected_examples: List[Path], model: str, base_name: str = None) -> None:
    """Log comprehensive statistics summary for the generation process."""
    # Calculate totals
    total_input_tokens = 0
    total_output_tokens = 0
    total_total_tokens = 0
    total_cached_tokens = 0
    
    if response_1.usage_metadata:
        total_input_tokens += getattr(response_1.usage_metadata, 'prompt_token_count', 0)
        total_output_tokens += getattr(response_1.usage_metadata, 'candidates_token_count', 0)
        total_total_tokens += getattr(response_1.usage_metadata, 'total_token_count', 0)
        total_cached_tokens += getattr(response_1.usage_metadata, 'cached_content_token_count', 0) if getattr(response_1.usage_metadata, 'cached_content_token_count', 0) is not None else 0
    
    if response_2.usage_metadata:
        total_input_tokens += getattr(response_2.usage_metadata, 'prompt_token_count', 0)
        total_output_tokens += getattr(response_2.usage_metadata, 'candidates_token_count', 0)
        total_total_tokens += getattr(response_2.usage_metadata, 'total_token_count', 0)
        total_cached_tokens += getattr(response_2.usage_metadata, 'cached_content_token_count', 0) if getattr(response_2.usage_metadata, 'cached_content_token_count', 0) is not None else 0
    
    if base_name:
        files_generated = [f"questions/{base_name}.json", f"surveys/{base_name}.json", f"responses/{base_name}.txt", f"html/{base_name}.html"]
    else:
        files_generated = ["questions/*.json", "surveys/*.json", "responses/*.txt", "html/*.html"]
    
    # Simple summary logging
    logger.info("")
    logger.info("=" * 50)
    logger.info("GENERATION SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total Input tokens:   {total_input_tokens:,}")
    logger.info(f"Total Output tokens:  {total_output_tokens:,}")
    logger.info(f"Total tokens used:    {total_total_tokens:,}")
    if total_cached_tokens > 0:
        logger.info(f"Cached tokens:        {total_cached_tokens:,}")
    logger.info(f"Examples used:        {len(selected_examples)}")
    logger.info(f"Files generated:      {len(files_generated)} ({', '.join(files_generated)})")
    logger.info(f"Model:                {model}")
    logger.info("=" * 50)