#!/bin/bash

# =============================================================================
# Batch Survey Generation Script
# =============================================================================
# This script processes all files in the inputs directory and generates
# SurveyJS JSON configurations for each one.
#
# Usage: ./batch_generate.sh
# 
# To modify parameters, edit the variables in the "Configuration" section below.
# =============================================================================

# Configuration - Modify these variables as needed
# =============================================================================

# Input directory containing files to process
INPUT_DIR="input"

# Output directory for generated surveys
OUTPUT_DIR="output"

# Model to use for generation
MODEL="gemini-2.5-pro-preview-05-06"

# Default pages to include (comma-separated list or "none" to skip)
# Options: introduction, consent, instructions, or "none"
DEFAULT_PAGES="introduction,consent"

# Directory containing default page templates
DEFAULT_PAGES_DIR="default_pages"

# Whether to use all examples (true) or prompt for selection (false)
ALL_EXAMPLES=true

# Whether to log statistics (true/false)
LOG_STATISTICS=true

# Debug mode - shows full command being executed (true/false)
DEBUG_MODE=true

# Maximum number of parallel jobs (adjust based on your system)
MAX_PARALLEL_JOBS=10

# File extensions to process (space-separated)
EXTENSIONS="pdf"

# =============================================================================
# Script Logic - Do not modify below unless you know what you're doing
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
print_status "Starting batch survey generation..."

# Check if virtual environment is activated or use uv
if [[ "$VIRTUAL_ENV" != "" ]]; then
    PYTHON_CMD="python"
    print_status "Using virtual environment: $VIRTUAL_ENV"
elif command -v uv &> /dev/null; then
    PYTHON_CMD="uv run python"
    print_status "Using uv for Python execution"
else
    print_error "No virtual environment detected and uv not found"
    print_error "Please activate your virtual environment or install uv"
    exit 1
fi

# Check if input directory exists
if [[ ! -d "$INPUT_DIR" ]]; then
    print_error "Input directory '$INPUT_DIR' does not exist"
    exit 1
fi

# Check if main.py exists
if [[ ! -f "main.py" ]]; then
    print_error "main.py not found in current directory"
    exit 1
fi

# Count total files to process
total_files=0
for ext in $EXTENSIONS; do
    count=$(find "$INPUT_DIR" -name "*.$ext" -type f | wc -l)
    total_files=$((total_files + count))
done

if [[ $total_files -eq 0 ]]; then
    print_warning "No files found with extensions: $EXTENSIONS"
    exit 0
fi

print_status "Found $total_files files to process"
print_status "Configuration:"
print_status "  Model: $MODEL"
print_status "  Default pages: $DEFAULT_PAGES"
print_status "  All examples: $ALL_EXAMPLES"
print_status "  Output directory: $OUTPUT_DIR"

# Build command options array
cmd_options=()
cmd_options+=("--model" "$MODEL")
cmd_options+=("--output" "$OUTPUT_DIR")
cmd_options+=("--default-pages" "$DEFAULT_PAGES")
cmd_options+=("--default-pages-dir" "$DEFAULT_PAGES_DIR")

if [[ "$ALL_EXAMPLES" == "true" ]]; then
    cmd_options+=("--all-examples")
fi

if [[ "$LOG_STATISTICS" == "false" ]]; then
    cmd_options+=("--no-log-statistics")
fi

echo ""
print_status "Starting parallel processing with $MAX_PARALLEL_JOBS jobs..."

# Function to process a single file
process_file() {
    local file="$1"
    local file_num="$2"
    local total="$3"
    
    local filename=$(basename "$file")
    local start_time=$(date +%s)
    
    print_status "[$file_num/$total] Starting: $filename"
    
    # Build command string from exported options
    local cmd_string="main.py \"$file\" $cmd_options_str"
    
    if [[ "$DEBUG_MODE" == "true" ]]; then
        print_status "   Command: $PYTHON_CMD $cmd_string"
    fi
    
    # Execute command and capture output
    local output
    local exit_code
    if [[ "$PYTHON_CMD" == "uv run python" ]]; then
        output=$(eval "uv run python $cmd_string" 2>&1)
        exit_code=$?
    else
        output=$(eval "$PYTHON_CMD $cmd_string" 2>&1)
        exit_code=$?
    fi
    
    local end_time=$(date +%s)
    local elapsed=$((end_time - start_time))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "✓ Successfully processed: $filename (${minutes}m ${seconds}s)"
        echo "SUCCESS:$filename" >> /tmp/batch_results.$$
    else
        print_error "✗ Failed to process: $filename (${minutes}m ${seconds}s)"
        echo "   Error details:"
        echo "$output" | sed 's/^/   /'
        echo "FAILED:$filename" >> /tmp/batch_results.$$
    fi
    
    echo ""
}

# Convert cmd_options array to string for export
cmd_options_str=""
for opt in "${cmd_options[@]}"; do
    cmd_options_str="$cmd_options_str '$opt'"
done

# Export function and variables for parallel execution
export -f process_file
export -f print_status
export -f print_success
export -f print_error
export PYTHON_CMD
export cmd_options_str
export DEBUG_MODE
export RED GREEN YELLOW BLUE NC

# Create temporary file for results
> /tmp/batch_results.$$

# Collect all files to process
files_to_process=()
for ext in $EXTENSIONS; do
    for file in "$INPUT_DIR"/*.$ext; do
        # Check if glob didn't match any files
        [[ ! -f "$file" ]] && continue
        files_to_process+=("$file")
    done
done

# Process files in parallel using xargs
start_time=$(date +%s)

# Create a more robust parallel processing approach
file_counter=1
for file in "${files_to_process[@]}"; do
    # Use background jobs with job control
    (
        process_file "$file" "$file_counter" "$total_files"
    ) &
    
    # Limit number of parallel jobs
    if (( $(jobs -r | wc -l) >= MAX_PARALLEL_JOBS )); then
        wait  # Wait for any job to complete
    fi
    
    ((file_counter++))
done

# Wait for all background jobs to complete
wait

# Calculate elapsed time
end_time=$(date +%s)
elapsed=$((end_time - start_time))
minutes=$((elapsed / 60))
seconds=$((elapsed % 60))

# Count results from temporary file
if [[ -f /tmp/batch_results.$$ ]]; then
    successful=$(grep -c "^SUCCESS:" /tmp/batch_results.$$ 2>/dev/null || echo "0")
    failed=$(grep -c "^FAILED:" /tmp/batch_results.$$ 2>/dev/null || echo "0")
    rm -f /tmp/batch_results.$$
else
    successful=0
    failed=$total_files
fi

# Summary
echo "============================================================================="
print_status "Parallel batch processing complete!"
print_status "Total files: $total_files"
print_success "Successfully processed: $successful"
if [[ $failed -gt 0 ]]; then
    print_error "Failed: $failed"
fi
print_status "Time elapsed: ${minutes}m ${seconds}s"
print_status "Parallel jobs: $MAX_PARALLEL_JOBS"
echo "============================================================================="

if [[ $failed -gt 0 ]]; then
    exit 1
else
    exit 0
fi