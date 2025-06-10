"""Default pages management utilities."""

import logging
import orjson as json
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def validate_page_structure(page: dict) -> bool:
    """Validate that a page has the required SurveyJS structure."""
    required_fields = ["name", "elements"]
    return all(field in page for field in required_fields) and isinstance(page["elements"], list)


def load_default_pages(page_names: List[str], pages_dir: Path) -> List[dict]:
    """Load default page templates from JSON files."""
    if not page_names:
        return []
    
    pages = []
    for page_name in page_names:
        page_file = pages_dir / f"{page_name}.json"
        
        if not page_file.exists():
            logger.warning(f"Default page file not found: {page_file}")
            continue
            
        try:
            page_content = json.loads(page_file.read_text())
            if validate_page_structure(page_content):
                pages.append(page_content)
                logger.info(f"Loaded default page: {page_name}")
            else:
                logger.warning(f"Invalid page structure in: {page_file}")
        except Exception as e:
            logger.warning(f"Could not load default page {page_file}: {e}")
    
    return pages


def format_default_pages_for_prompt(pages: List[dict]) -> str:
    """Format default pages as JSON string for prompt injection."""
    if not pages:
        return ""
    
    formatted_pages = []
    for i, page in enumerate(pages):
        # Ensure page names are properly sequenced
        page_copy = page.copy()
        page_copy["name"] = f"page{i}"
        formatted_pages.append(page_copy)
    
    try:
        return json.dumps(formatted_pages, option=json.OPT_INDENT_2).decode('utf-8')
    except Exception as e:
        logger.warning(f"Could not format default pages: {e}")
        return ""