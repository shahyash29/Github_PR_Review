# AI-Powered Git Commit Reviewer

An intelligent tool that automatically analyzes Git commits using Google's Gemini AI to provide quality scores, detailed feedback, and improvement suggestions for your code changes.

## Features

- **AI-Powered Analysis**: Uses Google Gemini 2.0 Flash to review commits for code quality, security, and best practices
- **GitHub Integration**: Automatically fetches and analyzes all repositories from a GitHub user
- **Quality Scoring**: Provides 1-10 quality scores for each commit
- **Detailed Feedback**: Get specific suggestions for code improvements
- **Professional Reports**: Generates both text and PDF reports with modern typography
- **Flexible Configuration**: Extensive customization through environment variables
- **Comprehensive Logging**: Detailed logging system for debugging and monitoring

## Prerequisites

- Python 3.8+
- Git installed and configured
- Google Gemini API key
- GitHub Personal Access Token (optional, for private repositories)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd git-commit-reviewer
```

### 2. Install Dependencies

#### Basic Installation
```bash
pip install requests python-dotenv
```

#### With PDF Generation Support
```bash
# For enhanced PDF with WeasyPrint
pip install requests python-dotenv weasyprint markdown

# OR for basic PDF with ReportLab
pip install requests python-dotenv reportlab

# For full functionality
pip install requests python-dotenv weasyprint markdown reportlab
```

### 3. Configuration

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional GitHub Configuration
GITHUB_TOKEN=your_github_token_here
DEFAULT_GITHUB_USERNAME=your_github_username

# Optional Configuration
DEFAULT_COMMIT_COUNT=5
MAX_DIFF_SIZE=3000
LOG_LEVEL=INFO
LOG_FILE=app.log
OUTPUT_DIR=/path/to/output/directory

# Git Configuration
GIT_USER_NAME=GitHub PR Reviewer
GIT_USER_EMAIL=reviewer@localhost
```

## API Keys Setup

### Google Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GEMINI_API_KEY`

### GitHub Token (Optional)
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` scope
3. Add it to your `.env` file as `GITHUB_TOKEN`

## Usage

### Basic Usage
```bash
python git_commit_reviewer.py --github-username yourusername
```

### Advanced Usage
```bash
# Analyze specific number of commits
python git_commit_reviewer.py --github-username yourusername --commits 10

# Custom output file
python git_commit_reviewer.py --github-username yourusername --output my_review.txt

# Skip PDF generation
python git_commit_reviewer.py --github-username yourusername --no-pdf

# Enable debug logging
python git_commit_reviewer.py --github-username yourusername --log-level DEBUG

# Dry run (see what would be analyzed without running)
python git_commit_reviewer.py --github-username yourusername --dry-run
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--github-username` | GitHub username to analyze | From env or git config |
| `--github-token` | GitHub Personal Access Token | From `GITHUB_TOKEN` env |
| `--commits`, `-c` | Number of commits per repository | 5 |
| `--output`, `-o` | Output file path | Auto-generated |
| `--api-key` | Gemini API key | From `GEMINI_API_KEY` env |
| `--no-pdf` | Skip PDF generation | False |
| `--log-level` | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `--dry-run` | Show what would be done | False |

## Output Files

The tool generates several output files in the configured directory:

- **Text Report**: `commit_review_username_timestamp.txt` - Detailed markdown report
- **PDF Report**: `analysis_username_timestamp.pdf` - Professional PDF with modern typography
- **Log File**: `app.log` - Detailed application logs

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `GITHUB_TOKEN` | GitHub Personal Access Token | Optional |
| `DEFAULT_GITHUB_USERNAME` | Default GitHub username | Auto-detected |
| `DEFAULT_COMMIT_COUNT` | Commits to analyze per repo | 5 |
| `MAX_DIFF_SIZE` | Maximum diff size in characters | 3000 |
| `LOG_LEVEL` | Logging level | INFO |
| `LOG_FILE` | Log file path | app.log |
| `OUTPUT_DIR` | Output directory | ~/Desktop/Github_PR_Review |
| `GIT_USER_NAME` | Git user name for operations | GitHub PR Reviewer |
| `GIT_USER_EMAIL` | Git user email | reviewer@localhost |

### PDF Generation

The tool supports two PDF generation methods:

1. **WeasyPrint** (Recommended): Modern typography with CSS styling
2. **ReportLab**: Professional layout with tables and formatting

Install the appropriate dependencies based on your needs.

## Report Structure

### Text Report
- **Summary**: Total commits, average score, generation timestamp
- **Configuration**: Current settings and parameters
- **Detailed Reviews**: For each commit:
  - Commit hash, author, date, message
  - Quality score (1-10)
  - AI feedback and analysis
  - Specific improvement suggestions

### PDF Report
- Professional typography and layout
- Color-coded sections and headers
- Tables for commit metadata
- Formatted code snippets
- Page numbering and navigation

## What Gets Analyzed

The AI reviews each commit for:

- **Code Quality**: Clarity, readability, and maintainability
- **Security**: Potential vulnerabilities and security concerns
- **Performance**: Performance implications and optimizations
- **Best Practices**: Adherence to coding standards
- **Testing**: Test coverage and quality considerations
- **Documentation**: Documentation needs and clarity

## Troubleshooting

### Common Issues

**No repositories found**
- Check GitHub username spelling
- Verify GitHub token permissions for private repos
- Ensure repositories exist and are accessible

**PDF generation failed**
- Install PDF dependencies: `pip install weasyprint reportlab`
- Check system requirements for WeasyPrint
- Use `--no-pdf` flag to skip PDF generation

**API rate limits**
- Use GitHub token to increase rate limits
- Reduce number of commits with `--commits` parameter
- Add delays between API calls if needed

**Git configuration errors**
- Ensure Git is installed and configured
- Check Git user settings with `git config --list`
- Verify repository access permissions

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
python git_commit_reviewer.py --github-username yourusername --log-level DEBUG
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.


## Acknowledgments

- Google Gemini AI for intelligent code analysis
- GitHub API for repository access
- WeasyPrint and ReportLab for PDF generation
- Python ecosystem for excellent tooling

## Support

If you encounter any issues or have questions:

1. Check the troubleshooting section above
2. Review the log files for detailed error information
3. Open an issue on GitHub with:
   - Error message
   - Log file contents
   - Steps to reproduce
   - System information

---

**Happy Code Reviewing!**