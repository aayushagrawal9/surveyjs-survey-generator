#!/usr/bin/env python3
"""
Minimal typer CLI application with pydantic models.
"""

from datetime import datetime
import logging
import orjson as json
import os
import mimetypes
import typer
from google.genai.types import GenerateContentResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from google import genai
from google.genai import types
from joblib import Memory, expires_after

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f'logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()
logger.handlers[1].setLevel(logging.INFO)

memory = Memory("cache", verbose=0)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
app = typer.Typer(help="Your CLI application")

@memory.cache(cache_validation_callback=expires_after(hours=48))  # 48 hours TTL
def upload_file_to_gemini(file: Path, mime_type: str):  # TODO: gemini files expire after 48 hours
    logger.debug(f"Uploading file to Gemini: {file.name}, {mime_type}")
    return client.files.upload(file=file, config=types.UploadFileConfig(mime_type=mime_type))

@memory.cache()  # No TTL for call_gemini cache
def call_gemini(system_instruction: str, model: str = "gemini-2.5-flash-preview-05-20",
                contents=None,
                response_mime_type: str = "application/json",
                call_name: str = "API Call",
                cached_content: str = None) -> GenerateContentResponse:
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
        logger.info(f"  • Candidates tokens:  {getattr(usage, 'candidates_token_count', 0):,}")
        logger.info(f"  • Total tokens:       {getattr(usage, 'total_token_count', 0):,}")
        cached_tokens = getattr(usage, 'cached_content_token_count', None)
        if cached_tokens is not None and cached_tokens > 0:
            logger.info(f"  • Cached tokens:      {cached_tokens:,}")
    else:
        logger.info(f"✓ {call_name} completed (usage data unavailable)")
    
    return response

@memory.cache(cache_validation_callback=expires_after(minutes=60))  # 60-minute TTL to match Google cache
def create_examples_cache(examples_content: str, model: str = "gemini-2.5-flash-preview-05-20", system_instruction: str = None) -> str | None:
    """Create a Google Gemini context cache for examples with 60-minute TTL."""
    if not examples_content:
        return None
    
    logger.info("Creating context cache for examples (60 min TTL)")
    
    # Create cache with 60-minute TTL and system instruction
    cache_config = types.CreateCachedContentConfig(
        contents=[types.Content(
            role="user",
            parts=[types.Part.from_text(text=examples_content)]
        )],
        ttl="3600s",  # 60 minutes in seconds
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

def generate_survey_html(survey_json: str, html_file: Path) -> None:
    """Generate a self-contained HTML file with embedded survey JSON and JavaScript."""
    # Read the HTML template and JavaScript
    html_template = Path("index.html").read_text()

    html = html_template.replace("{{survey_json}}", survey_json)
    # Write the combined HTML file
    html_file.write_text(html)
    logger.info(f"Generated self-contained survey HTML: {html_file}")

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

@app.command()
def generate_json(
    file: Path = typer.Argument(help="Path to input file", exists=True, file_okay=True, dir_okay=False),
    mime_type: str | None = typer.Argument(None, help="MIME type of the input file"),
    model: str = typer.Option("gemini-2.5-flash-preview-05-20", help="Model to use"),
    output: Optional[Path] = typer.Option("render", help="Output directory"),
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
    questions_dir = output / "questions"
    surveys_dir = output / "surveys" 
    responses_dir = output / "responses"
    html_dir = output / "html"
    
    # Create directories
    for dir_path in [questions_dir, surveys_dir, responses_dir, html_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
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