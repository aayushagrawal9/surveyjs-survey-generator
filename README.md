# SurveyJS PDF Converter

Convert PDF questionnaires into interactive SurveyJS surveys using Google Gemini AI.

## Overview

This tool uses a two-stage AI pipeline to transform PDF questionnaires into modern, interactive web surveys:
1. **Extract** structured questions from PDF documents
2. **Generate** SurveyJS-compatible JSON with customizable templates

## Prerequisites

- Python 3.8+
- UV package manager
- Google Gemini API key

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set your API key:**
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

## Basic Usage

Convert a PDF questionnaire to an interactive survey:

```bash
uv run python main.py path/to/questionnaire.pdf --all-examples --default-pages consent
```

This generates organized output files:
- `questions/filename.json` - Extracted questions
- `surveys/filename.json` - SurveyJS survey definition
- `responses/filename.txt` - Raw AI response
- `html/filename.html` - Interactive survey webpage

## Model Selection

Choose different Gemini models based on your needs:

```bash
# Default: Fast and cost-effective
uv run python main.py questionnaire.pdf --model gemini-2.5-flash-preview-05-20

# Alternative: More capable but slower
uv run python main.py questionnaire.pdf --model gemini-2.5-pro-preview-05-20
```

**When model is not specified:** Uses `gemini-2.5-flash-preview-05-20` (fast, cost-effective)

## Examples and Learning

The tool learns from example surveys to improve output quality:

### Interactive Example Selection (Default)
```bash
uv run python main.py questionnaire.pdf
```
**When no examples flag is provided:** Shows an interactive menu to select specific examples

### Use All Examples
```bash
uv run python main.py questionnaire.pdf --all-examples
```
**Benefits:** Better pattern recognition, more consistent formatting

### Skip Examples
```bash
# Simply press Enter when prompted, or use --all-examples=false
```
**When no examples selected:** Generates survey without learning patterns (may be less consistent)

## Default Pages

Add standardized pages to your surveys:

### Include Default Pages
```bash
uv run python main.py questionnaire.pdf --default-pages "introduction,consent,instructions"
```

### Custom Pages Directory
```bash
uv run python main.py questionnaire.pdf --default-pages "welcome,privacy" --default-pages-dir custom_templates/
```

**When default-pages is not specified:** Defaults to `"none"` - no additional pages added

**Available default pages depend on your templates directory structure.**

## Output Options

### Custom Output Directory
```bash
uv run python main.py questionnaire.pdf --output results/
```
**When output is not specified:** Uses `output/` directory

### Disable Statistics Logging
```bash
uv run python main.py questionnaire.pdf --log-statistics=false
```
**When log-statistics is not specified:** Defaults to `true` - shows token usage and generation summary

## Batch Processing

Process multiple files efficiently:

```bash
# Create and run batch script
chmod +x batch_generate.sh
./batch_generate.sh
```

Configure parallel processing by editing the script's `MAX_JOBS` variable.

## File Types

**Supported input formats:**
- PDF documents
- Image files (PNG, JPG, etc.)
- Any file type supported by Google Gemini

**When MIME type is not specified:** Automatically detected from file extension

## Advanced Usage

### Complete Command Example
```bash
uv run python main.py medical_questionnaire.pdf \
  --model gemini-2.5-pro-preview-05-20 \
  --output surveys_output/ \
  --all-examples \
  --default-pages "introduction,consent,demographics,instructions" \
  --default-pages-dir templates/ \
  --log-statistics
```

### Help and Options
```bash
uv run python main.py --help
```

## Output Structure

```
output/
├── questions/     # Extracted questions JSON
├── surveys/       # SurveyJS survey definitions  
├── responses/     # Raw AI responses
└── html/          # Interactive survey webpages
```

## Features

- **Intelligent Caching:** Reduces API costs through file upload and context caching
- **Organized Output:** Separates different file types for easy management
- **Token Tracking:** Detailed usage statistics for cost monitoring
- **Flexible Templates:** Customizable default pages and examples
- **Parallel Processing:** Batch script for handling multiple files
- **Self-contained HTML:** Generated surveys work offline

## Troubleshooting

**API Key Issues:**
```bash
# Verify your API key is set
echo $GEMINI_API_KEY
```

**Permission Errors:**
```bash
# Make sure output directory is writable
mkdir -p output && chmod 755 output
```

**Large Files:**
- Use `gemini-2.5-flash-preview-05-20` for faster processing
- Enable `--all-examples` for better results on complex documents

## Examples Directory Structure

Store your example surveys in:
```
examples/
├── medical/
│   ├── intake_form.json
│   └── assessment.json
├── research/
│   └── study_questionnaire.json
└── custom/
    └── specialized_survey.json
```

The tool recursively finds all `.json` files for example selection.