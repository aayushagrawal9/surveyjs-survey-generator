# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the application
```bash
# Basic usage (single file)
python main.py <input_file> [--mime-type <type>] [--model <model>] [--output <dir>] [--all-examples]

# With default pages
python main.py <input_file> --default-pages "introduction,consent,instructions"

# Skip default pages (default behavior)
python main.py <input_file> --default-pages "none"
# or simply omit the flag (defaults to "none")
python main.py <input_file>

# Use custom default pages directory
python main.py <input_file> --default-pages "introduction,consent" --default-pages-dir "custom_pages"

# Disable statistics logging
python main.py <input_file> --no-log-statistics
```

### Batch processing
```bash
# Process all files in inputs/ directory in parallel (10 concurrent jobs)
./batch_generate.sh

# Configure batch processing by editing batch_generate.sh:
# - INPUT_DIR: source directory (default: "inputs")
# - OUTPUT_DIR: destination directory (default: "output") 
# - MAX_PARALLEL_JOBS: concurrent processes (default: 10)
# - DEFAULT_PAGES: pages to include (default: "introduction,consent")
# - MODEL: AI model to use
# - ALL_EXAMPLES: bypass example selection UI
```

### Dependencies management
```bash
# Option 1: Using pip with virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Option 2: Using uv (recommended)
uv run python main.py <input_file>

# Requires Python >=3.13
```

### Environment setup
```bash
# Required environment variable
export GEMINI_API_KEY="your_api_key_here"

# Virtual environment activation (if using pip)
source .venv/bin/activate
```

## Architecture

This is a CLI tool that converts PDF questionnaires and forms into interactive SurveyJS web surveys using Google's Gemini AI. The application follows a two-stage AI pipeline:

### Core Workflow
1. **Document Upload**: PDF/document files are uploaded to Gemini for processing
2. **Question Extraction**: First Gemini call extracts structured questions from the document using `prompts/extract_questions.txt`
3. **Survey Generation**: Second Gemini call converts extracted questions into SurveyJS JSON format using `prompts/render_survey.txt`
4. **Output Generation**: Creates HTML survey, JSON files, and response logs

### Key Components

**main.py**: Main CLI application with typer framework
- `generate_json()`: Primary command that orchestrates the conversion pipeline
- `call_gemini()`: Cached Gemini API wrapper with usage tracking
- `upload_file_to_gemini()`: File upload handler with 48-hour cache
- `create_examples_cache()`: Context caching for example surveys (60-min TTL)
- `load_default_pages()`: Loads and validates default page templates
- `format_default_pages_for_prompt()`: Formats default pages for AI prompt injection
- `validate_page_structure()`: Validates SurveyJS page JSON structure
- `log_statistics_summary()`: Comprehensive token usage and generation statistics
- `generate_survey_html()`: Creates self-contained HTML files with embedded surveys

**batch_generate.sh**: Parallel processing script for bulk conversions
- Processes multiple files concurrently (configurable job limit)
- Organized error reporting and progress tracking
- Configurable parameters via script variables

**Caching Strategy**: Uses joblib Memory for aggressive caching:
- File uploads: 48-hour TTL (matches Gemini file expiration)
- API calls: Permanent cache for reproducibility
- Examples cache: 60-minute TTL (matches Google cache)

**Example-Driven Learning**: The `/examples` directory contains SurveyJS JSON examples that are used as context for the AI to learn patterns and maintain consistency across generated surveys.

**Default Pages System**: The `/default_pages` directory contains reusable SurveyJS page templates that can be injected before AI-generated questions. Pages are JSON files with valid SurveyJS page structure and can include introduction, consent, instructions, demographics, or any custom content needed across surveys.

**Output Structure**: Each conversion creates organized files in the output directory:
- `output/questions/{filename}.json`: Extracted questions in XML format
- `output/surveys/{filename}.json`: Final SurveyJS configuration  
- `output/html/{filename}.html`: Self-contained HTML file with embedded survey
- `output/responses/{filename}.txt`: Complete Gemini response for debugging

### Prompt Engineering
- `extract_questions.txt`: Converts documents to structured XML question format
- `render_survey.txt`: Transforms questions into SurveyJS JSON with one question per page
- Examples are dynamically injected into prompts for pattern learning

### Token Management
Comprehensive token usage tracking and logging with support for cached content tokens to optimize costs when using context caching. The `log_statistics_summary()` function provides detailed breakdowns of:
- Input/output token counts per API call
- Cached content token usage
- Total processing costs
- Generation time and file counts

### Parallel Processing
The `batch_generate.sh` script enables efficient bulk processing:
- **Job Control**: Configurable parallel job limits with proper background job management
- **Error Handling**: Individual file error reporting with detailed error messages
- **Progress Tracking**: Real-time status updates and completion statistics
- **Performance**: ~10x speed improvement over sequential processing

## Development Notes

- All file operations use pathlib.Path for cross-platform compatibility
- Logging configuration creates timestamped log files in `/logs` directory
- MIME type detection is automatic but can be overridden
- Interactive example selection UI unless `--all-examples` flag is used
- The application requires Gemini API access and handles file uploads, context caching, and token optimization
- Default pages are validated for proper SurveyJS structure before injection
- Output files are organized by type for better management and deployment