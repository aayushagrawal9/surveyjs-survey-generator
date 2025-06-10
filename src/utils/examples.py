"""Example selection and formatting utilities."""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Estimate token count using ~4 chars per token approximation."""
    return len(text) // 4


def select_examples() -> List[Path]:
    """Display examples and get user selection."""
    examples_dir = Path("examples")
    files = sorted(examples_dir.rglob("*.json"))
    
    print("\nAvailable examples:")
    for i, file_path in enumerate(files, 1):
        relative_path = file_path.relative_to(examples_dir)
        content = file_path.read_text()
        token_count = estimate_tokens(content)
        print(f"{i:2d}. {relative_path} ({token_count} tokens)")
    
    selection = input(f"\nEnter comma-separated IDs (1-{len(files)}), '*' for all, or press Enter to skip: ").strip()
    if not selection:
        return []
    
    if selection == "*":
        return files
    
    ids = [int(x.strip()) for x in selection.split(",")]
    selected_files = []
    
    for file_id in ids:
        selected_files.append(files[file_id - 1])
    
    return selected_files


def format_examples(selected_files: List[Path]) -> str:
    """Format selected example files for prompt."""
    if not selected_files:
        return ""
    
    examples_content = ""
    for i, file_path in enumerate(selected_files, 1):
        try:
            content = file_path.read_text()
            examples_content += f"Example {i}: ```json\n{content}\n```\n\n"
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")
    
    return examples_content