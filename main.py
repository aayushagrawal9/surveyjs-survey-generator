#!/usr/bin/env python3
"""
SurveyJS CLI application for converting PDF questionnaires to interactive surveys.
"""

import json
import mimetypes
import typer
from typing import Optional, List
from pathlib import Path
from google.genai import types

from src.config.logging import setup_logging
from src.config.settings import settings
from src.core.gemini_client import upload_file_to_gemini, call_gemini, create_examples_cache
from src.utils.default_pages import load_default_pages, format_default_pages_for_prompt
from src.utils.examples import select_examples, format_examples
from src.utils.file_ops import generate_survey_html, create_output_directories
from src.utils.stats import log_statistics_summary

# Setup logging and validate configuration
logger = setup_logging()
settings.validate()

app = typer.Typer(help="Convert PDF questionnaires to interactive SurveyJS surveys")


@app.command()
def main(
    file: Path = typer.Argument(help="Path to input file", exists=True, file_okay=True, dir_okay=False),
    mime_type: str | None = typer.Argument(None, help="MIME type of the input file"),
    model: str = typer.Option("gemini-2.5-flash-preview-05-20", help="Model to use"),
    output: Optional[Path] = typer.Option("output", help="Output directory"),
    all_examples: bool = typer.Option(False, "--all-examples", help="Use all examples and bypass selection UI"),
    log_statistics: bool = typer.Option(True, "--log-statistics", help="Log usage statistics"),
    default_pages: str = typer.Option("none", "--default-pages", help="Default pages to include (comma-separated list like 'introduction,consent,instructions' or 'none' to skip)"),
    default_pages_dir: Path = typer.Option("default_pages", "--default-pages-dir", help="Directory containing default page templates")
) -> None:
    """
    Generate JSON from an input file.
    """
    logger.info(f"Generating JSON for {file.name}")

    if mime_type is None:
        mime_type = mimetypes.guess_type(file)[0]

    # Create organized output directories
    base_name = file.stem
    questions_dir, surveys_dir, responses_dir, html_dir = create_output_directories(output)
    
    logger.info(f"Output base name: {base_name}")
    logger.info(f"Output directories: questions/, surveys/, responses/, html/")

    # Determine examples based on the --all-examples flag
    if all_examples:
        selected_examples = sorted(Path("examples").rglob("*.json"))
    else:
        selected_examples = select_examples()
    examples_content = format_examples(selected_examples)

    # Handle default pages
    default_pages_content = ""
    if default_pages.lower() != "none":
        page_names = [name.strip() for name in default_pages.split(",")]
        loaded_pages = load_default_pages(page_names, default_pages_dir)
        default_pages_content = format_default_pages_for_prompt(loaded_pages)
        if default_pages_content:
            logger.info(f"Loaded {len(loaded_pages)} default pages: {', '.join(page_names)}")
    else:
        logger.info("Skipping default pages")

    logger.info(f"Uploading file to Gemini: {file.name}, {mime_type}")
    uploaded_file: types.File = upload_file_to_gemini(file, mime_type)

    prompt_1 = open("prompts/extract_questions.txt").read()
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_1),
                types.Part.from_uri(
                    file_uri=uploaded_file.uri,
                    mime_type=uploaded_file.mime_type
                ),
            ],
        )
    ]

    logger.info(f"Calling Gemini: {model}")
    response_1 = call_gemini("You are an expert analyst transcribing questionnaires into machine readable formats",
                             model, contents, call_name="First API Call")
    survey_json = response_1.text
    questions_file = questions_dir / f"{base_name}.json"
    open(questions_file, "w").write(survey_json)
    logger.debug(f"Questions JSON saved to: {questions_file}")

    prompt_2 = open("prompts/render_survey.txt").read()
    prompt_2_with_questions = prompt_2.replace("{{questions}}", survey_json)
    prompt_2_with_default_pages = prompt_2_with_questions.replace("{{default_pages}}", default_pages_content)
    
    # System instruction for the second call
    system_instruction = "You are an expert SurveyJS JSON generator that learns from examples and applies consistent patterns. Only add personal data if it exists in the questionnaire. Do not use buttons or dropdowns."
    
    # Use context caching for examples if available
    if examples_content:
        # Create or retrieve a cache for examples with system instruction
        cache_name = create_examples_cache(examples_content, model, system_instruction)
    else:
        cache_name = None

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_2_with_default_pages)])]
    response_2 = call_gemini(system_instruction, model, contents, response_mime_type="text/plain",
                             call_name="Second API Call", cached_content=cache_name)

    gemini_response = response_2.text
    response_file = responses_dir / f"{base_name}.txt"
    open(response_file, "w").write(gemini_response)
    
    survey_json = gemini_response.split("```json")[1].split("```")[0]
    survey_file = surveys_dir / f"{base_name}.json"
    open(survey_file, "w").write(survey_json)
    logger.debug(f"Survey JSON saved to: {survey_file}")
    
    # Generate self-contained HTML
    html_file = html_dir / f"{base_name}.html"
    generate_survey_html(survey_json, html_file)
    logger.info(f"HTML saved to: {html_file}")


    if log_statistics:
        log_statistics_summary(response_1, response_2, selected_examples, model, base_name)

    logger.info(f"Generated all files for {file.name} in organized output structure")

if __name__ == "__main__":
    app()