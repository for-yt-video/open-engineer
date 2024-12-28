# Open Engineer 🚀

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)

Open Engineer is an AI-powered coding assistant that leverages the Qwen2.5-coder model through Ollama to provide intelligent code generation, editing, and project management capabilities. It offers a streamlined, interactive experience for developers working on both new and existing projects.

## Features ✨

- 🤖 **AI-Powered Code Generation** - Create new projects and files with intelligent suggestions
- ✏️ **Smart Code Editing** - Make precise changes to existing files with diff-based editing
- 💬 **Interactive Development** - Natural language interface for coding tasks
- 🔄 **Context-Aware** - Maintains conversation history for better understanding
- 📁 **Project Management** - Automatic project structure creation and organization
- 🔍 **File Integration** - Seamlessly add existing files to the conversation context

## Prerequisites 📋

Before you begin, ensure you have:

- Python 3.6 or higher installed
- [Ollama](https://ollama.ai/) installed and running locally
- Git for version control

## Installation 🛠️

1. Clone the repository:
```bash
git clone https://github.com/dustinwloring12988/open-engineer.git
cd open-engineer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Pull the required Ollama model:
```bash
ollama pull qwen2.5-coder:14b
```

## Usage 💻

1. Start the assistant:
```bash
python main.py
```

2. Describe your project when prompted
3. Interact with the assistant using natural language
4. Use `/add path/to/file` to include existing files in the conversation
5. Review and approve suggested changes

## Example Commands 📝

```bash
# Start a new project
python main.py
> Create a Flask web application with user authentication

# Add existing files to the conversation
> /add src/main.py
> Can you add error handling to this file?
```

## Project Structure 📂

```
open-engineer/
├── main.py              # Main application file
├── requirements.txt     # Python dependencies
├── LICENSE             # MIT license
├── README.md           # Project documentation
├── CONTRIBUTING.md     # Contribution guidelines
├── FAQ.md             # Frequently asked questions
├── projects/          # Generated project directory
└── logs/          # Generated logs directory
```

## Contributing 🤝

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

## Troubleshooting 🔧

For common issues and solutions, please refer to our [FAQ](FAQ.md). If you encounter any problems:

1. Check if Ollama is running (`ollama list`)
2. Verify your Python version and dependencies
3. Check the logs in the `logs/` directory
4. Open an issue if the problem persists

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support 💪

If you find this project helpful, please consider:
- Starring the repository
- Reporting issues
- Contributing to the codebase
- Sharing with other developers

## Contact 📧

- GitHub: [@dustinwloring12988](https://github.com/dustinwloring12988)
- Project Link: [https://github.com/dustinwloring12988/open-engineer](https://github.com/dustinwloring12988/open-engineer) 