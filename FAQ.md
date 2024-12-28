# Frequently Asked Questions (FAQ)

## General Questions

### What is Open Engineer?
Open Engineer is an AI-powered coding assistant that uses the Qwen model through Ollama to help with software development tasks. It provides intelligent code generation, editing, and project management capabilities.

### How does it work?
Open Engineer uses a streaming interface to communicate with the Qwen model through Ollama's API. It can create new files, edit existing ones, and provide contextual coding assistance while maintaining a conversation history.

### What are the system requirements?
- Python 3.6 or higher
- Ollama installed and running locally
- Required Python packages (listed in requirements.txt)
- Sufficient disk space for project generation

## Technical Questions

### How do I install Ollama?
Visit [Ollama's official website](https://ollama.ai/) for installation instructions for your operating system.

### How do I set up the environment?
1. Clone the repository
2. Create a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Ensure Ollama is running
5. Run `main.py`

### What models are supported?
Currently, the project uses the Qwen2.5-coder:14b model through Ollama. Support for other models may be added in future releases.

## Usage Questions

### How do I start a new project?
Run the main script and provide a description of your project. The assistant will help create an appropriately named directory and initial project structure.

### Can I use it with existing projects?
Yes! You can use the `/add` command to include existing files in the conversation context, allowing the assistant to understand and modify your existing codebase.

### How do I edit existing files?
The assistant can propose changes to existing files using a diff-based approach. You'll be shown the proposed changes and can approve or reject them before they're applied.

## Troubleshooting

### What if Ollama isn't responding?
1. Check if Ollama is running (`ollama list`)
2. Verify the OLLAMA_BASE_URL in your environment
3. Ensure you have the required model pulled (`ollama pull qwen2.5-coder:14b`)

### Why are my file edits not working?
1. Ensure the file exists and is readable
2. Check that the file content matches what the assistant expects
3. Verify you have write permissions for the file

### How do I report issues?
Please open an issue on the GitHub repository with:
1. A clear description of the problem
2. Steps to reproduce
3. Expected vs actual behavior
4. Any relevant error messages or logs

## Contributing

See our [CONTRIBUTING.md](CONTRIBUTING.md) file for information on how to contribute to the project.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. 