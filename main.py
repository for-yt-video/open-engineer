#!/usr/bin/env python3

import os
import sys
import json
import requests
import logging
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.style import Style
from rich.logging import RichHandler
from datetime import datetime

# Initialize Rich console and logging
console = Console()

# Configure logging with rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_path=True
        )
    ]
)

# Create logger instance
logger = logging.getLogger("qwen-engineer")

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Add file handler for persistent logging
file_handler = logging.FileHandler(
    logs_dir / f"qwen-engineer-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log",
    encoding='utf-8'
)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger.addHandler(file_handler)

# --------------------------------------------------------------------------------
# 1. Configure Ollama client and load environment variables
# --------------------------------------------------------------------------------
load_dotenv()  # Load environment variables from .env file
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "qwen2.5-coder:14b"

# --------------------------------------------------------------------------------
# 2. Define our schema using Pydantic for type safety
# --------------------------------------------------------------------------------
class ProjectNameResponse(BaseModel):
    """Response model for project naming request"""
    project_name: str
    explanation: str

class FileToCreate(BaseModel):
    path: str
    content: str

# NEW: Diff editing structure
class FileToEdit(BaseModel):
    path: str
    original_snippet: str
    new_snippet: str

class AssistantResponse(BaseModel):
    assistant_reply: str
    files_to_create: Optional[List[FileToCreate]] = None
    # NEW: optionally hold diff edits
    files_to_edit: Optional[List[FileToEdit]] = None

# --------------------------------------------------------------------------------
# 3. System prompts
# --------------------------------------------------------------------------------
project_naming_PROMPT = dedent("""\
    You are a project naming assistant. Your task is to create a suitable, concise folder name for a coding project based on the user's description.
    
    Guidelines for naming:
    1. Use lowercase letters, numbers, and hyphens only (no spaces or special characters)
    2. Keep it concise but descriptive (max 50 characters)
    3. Make it relevant to the project's purpose
    4. Avoid generic names like "project" or "app"
    5. Use hyphens to separate words
    
    You must respond in this JSON format:
    {
        "project_name": "your-suggested-name",
        "explanation": "A brief explanation of why this name was chosen"
    }
""")

system_PROMPT = dedent("""\
    You are an elite software engineer called Qwen Engineer with decades of experience across all programming domains.
    Your expertise spans system design, algorithms, testing, and best practices.
    You provide thoughtful, well-structured solutions while explaining your reasoning.

    Core capabilities:
    1. Code Analysis & Discussion
       - Analyze code with expert-level insight
       - Explain complex concepts clearly
       - Suggest optimizations and best practices
       - Debug issues with precision

    2. File Operations:
       a) Read existing files
          - Access user-provided file contents for context
          - Analyze multiple files to understand project structure
       
       b) Create new files
          - Generate complete new files with proper structure
          - Create complementary files (tests, configs, etc.)
       
       c) Edit existing files
          - Make precise changes using diff-based editing
          - Modify specific sections while preserving context
          - Suggest refactoring improvements

    Output Format:
    You must provide responses in this JSON structure:
    {
      "assistant_reply": "Your main explanation or response",
      "files_to_create": [
        {
          "path": "path/to/new/file",
          "content": "complete file content"
        }
      ],
      "files_to_edit": [
        {
          "path": "path/to/existing/file",
          "original_snippet": "exact code to be replaced",
          "new_snippet": "new code to insert"
        }
      ]
    }

    Guidelines:
    1. For normal responses, use 'assistant_reply'
    2. When creating files, include full content in 'files_to_create'
    3. For editing files:
       - Use 'files_to_edit' for precise changes
       - Include enough context in original_snippet to locate the change
       - Ensure new_snippet maintains proper indentation
       - Prefer targeted edits over full file replacements
    4. Always explain your changes and reasoning
    5. Consider edge cases and potential impacts
    6. Follow language-specific best practices
    7. Suggest tests or validation steps when appropriate

    Remember: You're a senior engineer - be thorough, precise, and thoughtful in your solutions.
""")

# --------------------------------------------------------------------------------
# 4. Helper functions 
# --------------------------------------------------------------------------------

def read_local_file(file_path: str) -> str:
    """Return the text content of a local file."""
    logger.debug(f"Reading file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    logger.debug(f"Successfully read {len(content)} bytes from {file_path}")
    return content

def create_file(path: str, content: str, project_dir: Path):
    """Create (or overwrite) a file at 'path' with the given 'content'."""
    file_path = project_dir / path
    file_path.parent.mkdir(parents=True, exist_ok=True)  # ensures any dirs exist
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Created/updated file: {file_path}")
    console.print(f"[green]✓[/green] Created/updated file at '[cyan]{file_path}[/cyan]'")
    
    # Record the action
    conversation_history.append({
        "role": "assistant",
        "content": f"✓ Created/updated file at '{file_path}'"
    })
    
    # Add the actual content to conversation context
    normalized_path = normalize_path(str(file_path))
    conversation_history.append({
        "role": "system",
        "content": f"Content of file '{normalized_path}':\n\n{content}"
    })

# NEW: Show the user a table of proposed edits and confirm
def show_diff_table(files_to_edit: List[FileToEdit]) -> None:
    if not files_to_edit:
        return
    
    logger.info(f"Showing diff table for {len(files_to_edit)} file(s)")
    # Enable multi-line rows by setting show_lines=True
    table = Table(title="Proposed Edits", show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("File Path", style="cyan")
    table.add_column("Original", style="red")
    table.add_column("New", style="green")

    for edit in files_to_edit:
        table.add_row(edit.path, edit.original_snippet, edit.new_snippet)
        logger.debug(f"Diff for {edit.path}:\nOriginal:\n{edit.original_snippet}\nNew:\n{edit.new_snippet}")
    
    console.print(table)

# NEW: Apply diff edits
def apply_diff_edit(path: str, original_snippet: str, new_snippet: str, project_dir: Path):
    """Reads the file at 'path', replaces the first occurrence of 'original_snippet' with 'new_snippet', then overwrites."""
    try:
        file_path = project_dir / path
        logger.info(f"Applying diff edit to {file_path}")
        content = read_local_file(file_path)
        if original_snippet in content:
            updated_content = content.replace(original_snippet, new_snippet, 1)
            create_file(path, updated_content, project_dir)  # This will now also update conversation context
            logger.info(f"Successfully applied diff edit to {file_path}")
            console.print(f"[green]✓[/green] Applied diff edit to '[cyan]{file_path}[/cyan]'")
            conversation_history.append({
                "role": "assistant",
                "content": f"✓ Applied diff edit to '{file_path}'"
            })
        else:
            logger.warning(f"Original snippet not found in {file_path}")
            console.print(f"[yellow]⚠[/yellow] Original snippet not found in '[cyan]{file_path}[/cyan]'. No changes made.", style="yellow")
            console.print("\nExpected snippet:", style="yellow")
            console.print(Panel(original_snippet, title="Expected", border_style="yellow"))
            console.print("\nActual file content:", style="yellow")
            console.print(Panel(content, title="Actual", border_style="yellow"))
    except FileNotFoundError:
        error_msg = f"File not found for diff editing: {file_path}"
        logger.error(error_msg)
        console.print(f"[red]✗[/red] {error_msg}", style="red")

def try_handle_add_command(user_input: str) -> bool:
    """
    If user_input starts with '/add ', read that file and insert its content
    into conversation as a system message. Returns True if handled; else False.
    """
    prefix = "/add "
    if user_input.strip().lower().startswith(prefix):
        file_path = user_input[len(prefix):].strip()
        try:
            logger.info(f"Adding file to conversation: {file_path}")
            content = read_local_file(file_path)
            conversation_history.append({
                "role": "system",
                "content": f"Content of file '{file_path}':\n\n{content}"
            })
            logger.info(f"Successfully added file to conversation: {file_path}")
            console.print(f"[green]✓[/green] Added file '[cyan]{file_path}[/cyan]' to conversation.\n")
        except OSError as e:
            error_msg = f"Could not add file '{file_path}': {e}"
            logger.error(error_msg)
            console.print(f"[red]✗[/red] {error_msg}\n", style="red")
        return True
    return False

def ensure_file_in_context(file_path: str) -> bool:
    """
    Ensures the file content is in the conversation context.
    Returns True if successful, False if file not found.
    """
    try:
        logger.debug(f"Ensuring file in context: {file_path}")
        normalized_path = normalize_path(file_path)
        content = read_local_file(normalized_path)
        file_marker = f"Content of file '{normalized_path}'"
        if not any(file_marker in msg["content"] for msg in conversation_history):
            logger.debug(f"Adding file to conversation context: {normalized_path}")
            conversation_history.append({
                "role": "system",
                "content": f"{file_marker}:\n\n{content}"
            })
        return True
    except OSError:
        error_msg = f"Could not read file '{file_path}' for editing context"
        logger.error(error_msg)
        console.print(f"[red]✗[/red] {error_msg}", style="red")
        return False

def normalize_path(path_str: str) -> str:
    """Return a canonical, absolute version of the path."""
    return str(Path(path_str).resolve())

# --------------------------------------------------------------------------------
# 5. Conversation state
# --------------------------------------------------------------------------------
conversation_history = [
    {"role": "system", "content": system_PROMPT}
]

# --------------------------------------------------------------------------------
# 6. OpenAI API interaction with streaming
# --------------------------------------------------------------------------------

def guess_files_in_message(user_message: str) -> List[str]:
    """
    Attempt to guess which files the user might be referencing.
    Returns normalized absolute paths.
    """
    recognized_extensions = [".css", ".html", ".js", ".py", ".json", ".md"]
    potential_paths = []
    for word in user_message.split():
        if any(ext in word for ext in recognized_extensions) or "/" in word:
            path = word.strip("',\"")
            try:
                normalized_path = normalize_path(path)
                potential_paths.append(normalized_path)
            except (OSError, ValueError):
                continue
    return potential_paths

def stream_openai_response(user_message: str):
    """
    Streams the Ollama chat completion response and handles structured output.
    Returns the final AssistantResponse.
    """
    logger.info("Starting new chat completion request")
    
    # Attempt to guess which file(s) user references
    potential_paths = guess_files_in_message(user_message)
    logger.debug(f"Detected potential file paths: {potential_paths}")
    
    valid_files = {}

    # Try to read all potential files before the API call
    for path in potential_paths:
        try:
            content = read_local_file(path)
            valid_files[path] = content  # path is already normalized
            file_marker = f"Content of file '{path}'"
            # Add to conversation if we haven't already
            if not any(file_marker in msg["content"] for msg in conversation_history):
                logger.debug(f"Adding new file to conversation context: {path}")
                conversation_history.append({
                    "role": "system",
                    "content": f"{file_marker}:\n\n{content}"
                })
        except OSError:
            error_msg = f"Cannot proceed: File '{path}' does not exist or is not accessible"
            logger.error(error_msg)
            console.print(f"[red]✗[/red] {error_msg}", style="red")
            continue

    # Now proceed with the API call
    conversation_history.append({"role": "user", "content": user_message})
    logger.debug("Added user message to conversation history")

    try:
        # Format messages for Ollama API
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in conversation_history]
        logger.debug(f"Prepared {len(messages)} messages for API request")
        
        # Make streaming request to Ollama
        logger.info(f"Making streaming request to Ollama API with model {MODEL_NAME}")
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": True,
                "format": "json"
            },
            stream=True
        )
        response.raise_for_status()
        logger.debug("Successfully initiated streaming response")

        console.print("\nAssistant> ", style="bold blue", end="")
        full_content = ""

        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    if "message" in chunk and "content" in chunk["message"]:
                        content_chunk = chunk["message"]["content"]
                        full_content += content_chunk
                        console.print(content_chunk, end="")
                except json.JSONDecodeError:
                    logger.warning("Failed to parse streaming chunk as JSON")
                    continue

        console.print()
        logger.debug("Finished receiving streaming response")

        try:
            logger.debug("Attempting to parse full response as JSON")
            parsed_response = json.loads(full_content)
            
            # Ensure assistant_reply is present
            if "assistant_reply" not in parsed_response:
                logger.debug("Adding empty assistant_reply to response")
                parsed_response["assistant_reply"] = ""

            # If assistant tries to edit files not in valid_files, remove them
            if "files_to_edit" in parsed_response and parsed_response["files_to_edit"]:
                logger.info(f"Processing {len(parsed_response['files_to_edit'])} file edit requests")
                new_files_to_edit = []
                for edit in parsed_response["files_to_edit"]:
                    try:
                        edit_abs_path = normalize_path(edit["path"])
                        # If we have the file in context or can read it now
                        if edit_abs_path in valid_files or ensure_file_in_context(edit_abs_path):
                            edit["path"] = edit_abs_path  # Use normalized path
                            new_files_to_edit.append(edit)
                            logger.debug(f"Validated file edit for: {edit_abs_path}")
                    except (OSError, ValueError):
                        logger.warning(f"Invalid path in edit request: {edit['path']}")
                        console.print(f"[yellow]⚠[/yellow] Skipping invalid path: '{edit['path']}'", style="yellow")
                        continue
                parsed_response["files_to_edit"] = new_files_to_edit

            response_obj = AssistantResponse(**parsed_response)
            logger.info("Successfully created AssistantResponse object")

            # Save the assistant's textual reply to conversation
            conversation_history.append({
                "role": "assistant",
                "content": response_obj.assistant_reply
            })
            logger.debug("Added assistant reply to conversation history")

            return response_obj

        except json.JSONDecodeError:
            error_msg = "Failed to parse JSON response from assistant"
            logger.error(f"{error_msg}. Response content: {full_content[:200]}...")
            console.print(f"[red]✗[/red] {error_msg}", style="red")
            return AssistantResponse(
                assistant_reply=error_msg,
                files_to_create=[]
            )

    except Exception as e:
        error_msg = f"Ollama API error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        console.print(f"\n[red]✗[/red] {error_msg}", style="red")
        return AssistantResponse(
            assistant_reply=error_msg,
            files_to_create=[]
        )

def get_project_name(user_message: str) -> str:
    """
    Makes an Ollama API call to get a suitable project name based on the user's initial message.
    Returns the project name as a string.
    """
    logger.info("Requesting project name from Ollama")
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": project_naming_PROMPT},
                    {"role": "user", "content": f"Create a folder name for this project: {user_message}"}
                ],
                "stream": False,
                "format": "json"
            }
        )
        response.raise_for_status()
        
        try:
            result = response.json()
            if "message" in result and "content" in result["message"]:
                content = result["message"]["content"]
                project_info = ProjectNameResponse.parse_raw(content)
                logger.info(f"Generated project name: {project_info.project_name}")
                logger.debug(f"Project name explanation: {project_info.explanation}")
                return project_info.project_name
        except Exception as e:
            logger.error(f"Failed to parse project name response: {str(e)}")
            return "unnamed-project"
    
    except Exception as e:
        logger.error(f"Failed to get project name from Ollama: {str(e)}")
        return "unnamed-project"

def get_unique_project_dir(base_name: str, projects_dir: Path) -> str:
    """
    Returns a unique project name by appending a number if the base name already exists.
    For example, if 'my-project' exists, returns 'my-project-1', 'my-project-2', etc.
    """
    if not (projects_dir / base_name).exists():
        return base_name
    
    counter = 1
    while (projects_dir / f"{base_name}-{counter}").exists():
        counter += 1
    
    return f"{base_name}-{counter}"

# --------------------------------------------------------------------------------
# 7. Main interactive loop
# --------------------------------------------------------------------------------

def main():
    logger.info(f"Starting Qwen Engineer session with model: {MODEL_NAME}")
    logger.info(f"Using Ollama API at: {OLLAMA_BASE_URL}")
    
    console.print(Panel.fit(
        f"[bold blue]Welcome to Qwen Engineer ({MODEL_NAME}) with Structured Output[/bold blue] [green](and streaming)[/green]!🚀",
        border_style="blue"
    ))
    
    # Get initial project description from user
    console.print("\nFirst, please describe your project idea:", style="bold cyan")
    project_description = console.input("[bold green]You>[/bold green] ").strip()
    
    if not project_description:
        logger.warning("No project description provided, using default name")
        base_project_name = "unnamed-project"
    else:
        base_project_name = get_project_name(project_description)
    
    # Create project directory with unique name
    projects_dir = Path("projects")
    projects_dir.mkdir(exist_ok=True)
    
    # Get unique project name
    project_name = get_unique_project_dir(base_project_name, projects_dir)
    project_dir = projects_dir / project_name
    project_dir.mkdir(exist_ok=True)
    
    logger.info(f"Project directory created: {project_dir}")
    console.print(f"\n[green]✓[/green] Created project directory: [cyan]{project_dir}[/cyan]")
    console.print(
        "\nTo include a file in the conversation, use '[bold magenta]/add path/to/file[/bold magenta]'.\n"
        "Type '[bold red]exit[/bold red]' or '[bold red]quit[/bold red]' to end.\n"
    )

    # Process the initial project description as the first message
    if project_description:
        logger.info("Processing initial project description")
        response_data = stream_openai_response(project_description)

        # Create any files if requested
        if response_data.files_to_create:
            logger.info(f"Processing {len(response_data.files_to_create)} file creation requests")
            for file_info in response_data.files_to_create:
                create_file(file_info.path, file_info.content, project_dir)

        # Show and confirm diff edits if requested
        if response_data.files_to_edit:
            logger.info(f"Processing {len(response_data.files_to_edit)} file edit requests")
            show_diff_table(response_data.files_to_edit)
            confirm = console.input(
                "\nDo you want to apply these changes? ([green]y[/green]/[red]n[/red]): "
            ).strip().lower()
            
            if confirm == 'y':
                logger.info("User confirmed file edits")
                for edit_info in response_data.files_to_edit:
                    apply_diff_edit(edit_info.path, edit_info.original_snippet, edit_info.new_snippet, project_dir)
            else:
                logger.info("User rejected file edits")
                console.print("[yellow]ℹ[/yellow] Skipped applying diff edits.", style="yellow")

    while True:
        try:
            user_input = console.input("[bold green]You>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("Session terminated by keyboard interrupt")
            console.print("\n[yellow]Exiting.[/yellow]")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            logger.info("Session terminated by user command")
            console.print("[yellow]Goodbye![/yellow]")
            break

        logger.info("Processing user input")
        logger.debug(f"User input: {user_input}")

        # If user is reading a file
        if try_handle_add_command(user_input):
            continue

        # Get streaming response from Ollama
        response_data = stream_openai_response(user_input)

        # Create any files if requested
        if response_data.files_to_create:
            logger.info(f"Processing {len(response_data.files_to_create)} file creation requests")
            for file_info in response_data.files_to_create:
                create_file(file_info.path, file_info.content, project_dir)

        # Show and confirm diff edits if requested
        if response_data.files_to_edit:
            logger.info(f"Processing {len(response_data.files_to_edit)} file edit requests")
            show_diff_table(response_data.files_to_edit)
            confirm = console.input(
                "\nDo you want to apply these changes? ([green]y[/green]/[red]n[/red]): "
            ).strip().lower()
            
            if confirm == 'y':
                logger.info("User confirmed file edits")
                for edit_info in response_data.files_to_edit:
                    apply_diff_edit(edit_info.path, edit_info.original_snippet, edit_info.new_snippet, project_dir)
            else:
                logger.info("User rejected file edits")
                console.print("[yellow]ℹ[/yellow] Skipped applying diff edits.", style="yellow")

    logger.info("Session finished")
    console.print("[blue]Session finished.[/blue]")

if __name__ == "__main__":
    main()
