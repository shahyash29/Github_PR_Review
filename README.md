# AI-Powered Git Commit Reviewer

An intelligent tool that analyzes Git commits across repositories using AI to provide comprehensive code review feedback.

## Features

- **Multi-Repository Support**: Scan and review commits across multiple Git repositories
- **AI-Powered Analysis**: Uses OpenAI GPT to provide intelligent code review feedback
- **Quality Scoring**: Assigns quality scores (1-10) to commits
- **Detailed Reports**: Generates comprehensive review reports
- **Focused Reviews**: Analyzes code clarity, security, performance, and best practices
- **Batch Processing**: Review multiple commits at once

## Installation

1. Clone or download this tool
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Basic Usage

Review commits in current directory:
```bash
python git_commit_reviewer.py
```

### Review Specific Repository

```bash
python git_commit_reviewer.py --repo /path/to/your/repository
```

### Review Multiple Repositories

```bash
python git_commit_reviewer.py --path /path/to/parent/directory
```

### Advanced Options

```bash
# Review last 10 commits and save report
python git_commit_reviewer.py --commits 10 --output review_report.md

# Use specific API key
python git_commit_reviewer.py --api-key "your-key" --repo /path/to/repo
```

## Command Line Options

- `--path, -p`: Path to search for Git repositories (default: current directory)
- `--repo, -r`: Specific repository path to review
- `--commits, -c`: Number of recent commits to review (default: 5)
- `--output, -o`: Output file for the report
- `--api-key`: OpenAI API key (or set OPENAI_API_KEY environment variable)

## What It Analyzes

The AI reviewer evaluates commits based on:

- **Code Quality**: Clarity, readability, and maintainability
- **Security**: Potential security vulnerabilities and concerns
- **Performance**: Performance implications of changes
- **Best Practices**: Adherence to coding standards and conventions
- **Testing**: Test coverage and testing considerations
- **Documentation**: Documentation needs and clarity

## Sample Output

```
# Git Commit Review Report
Generated on: 2024-01-20 15:30:45

## Summary
Total commits reviewed: 5
Average quality score: 7.8/10

## Detailed Reviews

### Commit: a1b2c3d4
**Author:** John Doe
**Date:** 2024-01-20 14:25:30
**Message:** Add user authentication middleware
**Quality Score:** 8/10

**Feedback:**
Good implementation of authentication middleware. Code is well-structured and follows security best practices...

**Suggestions:**
- Add unit tests for edge cases
- Consider adding rate limiting
- Document the middleware usage
```

## Configuration

You can set the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (required for AI analysis)

## Requirements

- Python 3.7+
- Git installed and accessible from command line
- OpenAI API key for AI analysis
- Internet connection for API calls

## Limitations

- Requires OpenAI API key for AI-powered analysis
- Large commits may be truncated for analysis
- API rate limits may affect batch processing of many commits

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.