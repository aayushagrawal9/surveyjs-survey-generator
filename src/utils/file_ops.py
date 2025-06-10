"""File operations and HTML generation utilities."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_survey_html(survey_json: str, html_file: Path) -> None:
    """Generate a self-contained HTML file with embedded survey JSON and JavaScript."""
    # Read the HTML template and JavaScript
    html_template = Path("index.html").read_text()

    html = html_template.replace("{{survey_json}}", survey_json)
    # Write the combined HTML file
    html_file.write_text(html)
    logger.info(f"Generated self-contained survey HTML: {html_file}")


def create_output_directories(output: Path) -> tuple[Path, Path, Path, Path]:
    """Create organized output directories and return paths."""
    questions_dir = output / "questions"
    surveys_dir = output / "surveys" 
    responses_dir = output / "responses"
    html_dir = output / "html"
    
    # Create directories
    for dir_path in [questions_dir, surveys_dir, responses_dir, html_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return questions_dir, surveys_dir, responses_dir, html_dir