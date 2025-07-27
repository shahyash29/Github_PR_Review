import os
import sys
import json
import subprocess
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional
import requests
import tempfile
import shutil

try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    from weasyprint import HTML, CSS
    import markdown
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class GitCommitReviewer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.max_diff_size = int(os.getenv('MAX_DIFF_SIZE', '3000'))
        self.default_commit_count = int(os.getenv('DEFAULT_COMMIT_COUNT', '5'))
        self.setup_logging()
        self.setup_git_config()
        
        if not self.api_key:
            self.logger.warning("No Gemini API key found. Set GEMINI_API_KEY environment variable.")

    def setup_logging(self):
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_file = os.getenv('LOG_FILE', 'app.log')
        
        log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else '.'
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")

    def setup_git_config(self):
        git_user_name = os.getenv('GIT_USER_NAME', 'GitHub PR Reviewer')
        git_user_email = os.getenv('GIT_USER_EMAIL', 'reviewer@localhost')
        
        try:
            subprocess.run(['git', 'config', '--global', 'user.name', git_user_name], check=True, capture_output=True)
            subprocess.run(['git', 'config', '--global', 'user.email', git_user_email], check=True, capture_output=True)
            subprocess.run(['git', 'config', '--global', 'init.defaultBranch', 'main'], check=True, capture_output=True)
            subprocess.run(['git', 'config', '--global', 'pull.rebase', 'false'], check=True, capture_output=True)
            self.logger.info(f"Git configured: {git_user_name} <{git_user_email}>")
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to configure Git: {e}")

    def get_recent_commits(self, repo_path: str, count: int = None) -> List[Dict]:
        if count is None:
            count = self.default_commit_count
            
        try:
            original_dir = os.getcwd()
            os.chdir(repo_path)
            cmd = [
                'git', 'log', '--oneline', '--no-merges',
                f'-{count}', '--pretty=format:%H|%an|%ad|%s',
                '--date=iso'
            ]
            
            self.logger.debug(f"Running git command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            'hash': parts[0],
                            'author': parts[1],
                            'date': parts[2],
                            'message': parts[3]
                        })
            
            self.logger.info(f"Found {len(commits)} commits in {os.path.basename(repo_path)}")
            return commits
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Error getting commits from {repo_path}: {e}"
            self.logger.error(error_msg)
            return []
        finally:
            os.chdir(original_dir)

    def get_commit_diff(self, repo_path: str, commit_hash: str) -> str:
        try:
            original_dir = os.getcwd()
            os.chdir(repo_path)
            cmd = ['git', 'show', '--no-merges', commit_hash]
            
            self.logger.debug(f"Getting diff for commit {commit_hash[:8]}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Error getting diff for commit {commit_hash}: {e}"
            self.logger.error(error_msg)
            return ""
        finally:
            os.chdir(original_dir)

    def clone_repository_with_auth(self, clone_url: str, repo_path: str, token: str = None) -> bool:
        try:
            if token and clone_url.startswith('https://github.com/'):
                auth_url = clone_url.replace('https://github.com/', f'https://{token}@github.com/')
                clone_url = auth_url
            
            cmd = ['git', 'clone', '--depth', '1', clone_url, repo_path]
            cmd_log = ['git', 'clone', '--depth', '1', clone_url.replace(token, '***') if token else clone_url, repo_path]
            self.logger.debug(f"Running: {' '.join(cmd_log)}")
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone {clone_url}: {e}")
            return False

    def analyze_commit_with_ai(self, commit_info: Dict, diff_content: str) -> Dict:
        if not self.api_key:
            return {
                'score': 'N/A',
                'feedback': 'AI analysis unavailable - no API key configured',
                'suggestions': []
            }

        limited_diff = diff_content[:self.max_diff_size]
        if len(diff_content) > self.max_diff_size:
            self.logger.debug(f"Diff truncated from {len(diff_content)} to {self.max_diff_size} characters")

        prompt = f"""
        Please review this Git commit and provide feedback:

        Commit Hash: {commit_info['hash']}
        Author: {commit_info['author']}
        Date: {commit_info['date']}
        Message: {commit_info['message']}

        Diff:
        {limited_diff}

        Please analyze this commit and provide:
        1. A quality score (1-10)
        2. Overall feedback
        3. Specific suggestions for improvement
        4. Code quality concerns
        5. Best practices compliance

        Focus on:
        - Code clarity and readability
        - Potential bugs or issues
        - Security concerns
        - Performance implications
        - Testing considerations
        - Documentation needs
        """
        
        try:
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key
            }
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            self.logger.debug(f"Making API request for commit {commit_info['hash'][:8]}")
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers=headers,
                json=data,
                timeout=30
            )
            
            self.logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                ai_feedback = (
                    result.get("candidates", [{}])[0]
                          .get("content", {})
                          .get("parts", [{}])[0]
                          .get("text", "")
                )
                
                analysis_result = {
                    'score': self._extract_score(ai_feedback),
                    'feedback': ai_feedback,
                    'suggestions': self._extract_suggestions(ai_feedback)
                }
                
                self.logger.debug(f"Analysis completed for commit {commit_info['hash'][:8]} - Score: {analysis_result['score']}")
                return analysis_result
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                self.logger.error(f"API Error Details: {response.text}")
                return {
                    'score': 'Error',
                    'feedback': error_msg,
                    'suggestions': []
                }
                
        except Exception as e:
            error_msg = f'Analysis failed: {str(e)}'
            self.logger.error(f"Exception during API call: {str(e)}")
            return {
                'score': 'Error',
                'feedback': error_msg,
                'suggestions': []
            }

    def _extract_score(self, feedback: str) -> str:
        import re
        
        score_patterns = [
            r'score[:\s]*(\d+)/10',
            r'score[:\s]*(\d+)\s*/\s*10',
            r'(\d+)/10',
            r'score[:\s]*(\d+)',
        ]
        
        feedback_lower = feedback.lower()
        
        for pattern in score_patterns:
            matches = re.findall(pattern, feedback_lower)
            if matches:
                score = matches[0]
                if score.isdigit() and 1 <= int(score) <= 10:
                    return score
        
        return 'N/A'

    def _extract_suggestions(self, feedback: str) -> List[str]:
        suggestions = []
        lines = feedback.split('\n')
        in_suggestions = False
        
        for line in lines:
            line = line.strip()
            if 'suggestion' in line.lower() or 'improve' in line.lower():
                in_suggestions = True
            elif in_suggestions and line.startswith(('-', '*', '•')):
                suggestions.append(line[1:].strip())
            elif in_suggestions and line and not line.startswith(('-', '*', '•')):
                in_suggestions = False
                
        return suggestions[:5]

    def generate_report(self, reviews: List[Dict], output_file: str = None) -> str:
        self.logger.info(f"Generating report for {len(reviews)} reviews")
        
        report = f"""# Git Commit Review Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Log Level: {os.getenv('LOG_LEVEL', 'INFO')}
Max Diff Size: {self.max_diff_size} characters

## Summary
Total commits reviewed: {len(reviews)}
"""
        if reviews:
            scores = [r['analysis']['score'] for r in reviews if r['analysis']['score'].isdigit()]
            if scores:
                avg_score = sum(int(s) for s in scores) / len(scores)
                report += f"Average quality score: {avg_score:.1f}/10\n"
                report += f"Scores distribution: {', '.join(scores)}\n"
        
        report += "\n## Detailed Reviews\n"
        
        for review in reviews:
            commit = review['commit']
            analysis = review['analysis']
            repo_name = os.path.basename(review['repository'])
            
            report += f"""
### Commit: {commit['hash'][:8]} ({repo_name})
**Author:** {commit['author']}  
**Date:** {commit['date']}  
**Message:** {commit['message']}  
**Quality Score:** {analysis['score']}/10

**Feedback:**
{analysis['feedback']}

**Suggestions:**
"""
            for suggestion in analysis['suggestions']:
                report += f"- {suggestion}\n"
            report += "\n---\n"
        
        if output_file:
            try:
                output_dir = os.path.dirname(os.path.abspath(output_file))
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                self.logger.info(f"Report saved to: {os.path.abspath(output_file)}")
                
            except Exception as e:
                error_msg = f"Error saving report to {output_file}: {e}"
                self.logger.error(error_msg)
        
        return report

    def create_custom_styles(self):
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))
        
        styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#1e293b'),
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=15,
            textColor=colors.HexColor('#2563eb'),
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='BodyText',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leading=16,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        styles.add(ParagraphStyle(
            name='Code',
            parent=styles['Normal'],
            fontSize=9,
            fontName='Courier',
            backColor=colors.HexColor('#f1f5f9'),
            borderWidth=1,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=8,
            spaceAfter=10,
            leftIndent=10,
            rightIndent=10
        ))
        
        return styles

    def generate_pdf_with_reportlab(self, reviews: List[Dict], output_dir: str, username: str) -> Optional[str]:
        if not REPORTLAB_AVAILABLE:
            self.logger.warning("ReportLab not available for PDF generation")
            return None
            
        try:
            self.logger.info("Generating PDF with ReportLab")
            pdf_filename = f"analysis_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            doc = SimpleDocTemplate(
                pdf_path, 
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            styles = self.create_custom_styles()
            story = []
            
            story.append(Paragraph("Git Commit Review Report", styles['CustomTitle']))
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph(f"Analysis for GitHub User: {username}", styles['Subtitle']))
            story.append(Spacer(1, 0.3*inch))
            
            config_text = f"""
            <b>Configuration:</b><br/>
            Max Diff Size: {self.max_diff_size} characters<br/>
            Default Commit Count: {self.default_commit_count}<br/>
            Log Level: {os.getenv('LOG_LEVEL', 'INFO')}
            """
            story.append(Paragraph(config_text, styles['BodyText']))
            story.append(Spacer(1, 0.2*inch))
            
            if reviews:
                scores = [r['analysis']['score'] for r in reviews if r['analysis']['score'].isdigit()]
                if scores:
                    avg_score = sum(int(s) for s in scores) / len(scores)
                    summary_text = f"""
                    <b>Total commits reviewed:</b> {len(reviews)}<br/>
                    <b>Average quality score:</b> {avg_score:.1f}/10<br/>
                    <b>Generated on:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                    """
                else:
                    summary_text = f"""
                    <b>Total commits reviewed:</b> {len(reviews)}<br/>
                    <b>Generated on:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                    """
            else:
                summary_text = "No commits reviewed"
                
            story.append(Paragraph(summary_text, styles['BodyText']))
            story.append(Spacer(1, 0.3*inch))
            
            story.append(Paragraph("─" * 80, styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("Detailed Commit Analysis", styles['SectionHeading']))
            
            for i, review in enumerate(reviews, 1):
                commit = review['commit']
                analysis = review['analysis']
                repo_name = os.path.basename(review['repository'])
                
                commit_title = f"#{i} - Commit: {commit['hash'][:8]} ({repo_name})"
                story.append(Paragraph(commit_title, styles['SubsectionHeading']))
                
                commit_data = [
                    ['Author', commit['author']],
                    ['Date', commit['date'][:19]],
                    ['Message', commit['message'][:100] + "..." if len(commit['message']) > 100 else commit['message']],
                    ['Quality Score', f"{analysis['score']}/10"]
                ]
                
                commit_table = Table(commit_data, colWidths=[1.5*inch, 4*inch])
                commit_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e293b')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                
                story.append(commit_table)
                story.append(Spacer(1, 0.1*inch))
                
                feedback = analysis['feedback']
                if len(feedback) > 800:
                    feedback = feedback[:800] + "..."
                
                story.append(Paragraph("<b>AI Analysis:</b>", styles['SubsectionHeading']))
                story.append(Paragraph(feedback, styles['BodyText']))
                
                if analysis['suggestions']:
                    story.append(Paragraph("<b>Improvement Suggestions:</b>", styles['SubsectionHeading']))
                    for suggestion in analysis['suggestions'][:3]:
                        story.append(Paragraph(f"• {suggestion}", styles['BodyText']))
                
                story.append(Spacer(1, 0.2*inch))
                
                if i % 3 == 0 and i < len(reviews):
                    story.append(PageBreak())
            
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("─" * 80, styles['Normal']))
            footer_text = f"Report generated by AI-Powered Git Commit Reviewer | {datetime.now().strftime('%Y')}"
            story.append(Paragraph(footer_text, styles['Subtitle']))
            
            doc.build(story)
            self.logger.info(f"PDF generated successfully: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            error_msg = f"Error generating PDF with reportlab: {e}"
            self.logger.error(error_msg)
            return None

    def generate_enhanced_pdf_with_weasyprint(self, report: str, output_dir: str, username: str) -> Optional[str]:
        if not PDF_AVAILABLE:
            self.logger.warning("WeasyPrint not available for PDF generation")
            return None
            
        try:
            self.logger.info("Generating PDF with WeasyPrint")
            css_content = """
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
            
            :root {
                --primary-color: #2563eb;
                --secondary-color: #64748b;
                --accent-color: #06b6d4;
                --success-color: #10b981;
                --text-primary: #1e293b;
                --text-secondary: #64748b;
                --background-color: #ffffff;
                --surface-color: #f8fafc;
                --border-color: #e2e8f0;
                --code-background: #f1f5f9;
            }
            
            @page {
                size: A4;
                margin: 2cm;
                @bottom-right {
                    content: counter(page);
                    font-family: 'Inter', sans-serif;
                    font-size: 9pt;
                    color: var(--text-secondary);
                }
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                line-height: 1.6;
                color: var(--text-primary);
                font-size: 11pt;
                margin: 0;
                padding: 0;
            }
            
            h1 {
                font-size: 24pt;
                font-weight: 700;
                color: var(--primary-color);
                text-align: center;
                margin-bottom: 0.5cm;
                border-bottom: 3px solid var(--primary-color);
                padding-bottom: 0.3cm;
            }
            
            h2 {
                font-size: 18pt;
                font-weight: 600;
                color: var(--text-primary);
                margin-top: 1cm;
                margin-bottom: 0.5cm;
                border-left: 4px solid var(--primary-color);
                padding-left: 0.3cm;
            }
            
            h3 {
                font-size: 14pt;
                font-weight: 600;
                color: var(--primary-color);
                margin-top: 0.8cm;
                margin-bottom: 0.3cm;
            }
            
            p {
                margin-bottom: 0.4cm;
                text-align: justify;
            }
            
            strong {
                font-weight: 600;
                color: var(--text-primary);
            }
            
            code {
                font-family: 'JetBrains Mono', Monaco, Consolas, monospace;
                font-size: 9pt;
                background-color: var(--code-background);
                padding: 0.1cm 0.2cm;
                border-radius: 0.1cm;
                color: var(--primary-color);
            }
            
            pre {
                background-color: var(--surface-color);
                border: 1px solid var(--border-color);
                border-radius: 0.2cm;
                padding: 0.5cm;
                margin: 0.5cm 0;
                font-family: 'JetBrains Mono', Monaco, Consolas, monospace;
                font-size: 9pt;
                overflow-wrap: break-word;
            }
            
            ul, ol {
                margin: 0.3cm 0;
                padding-left: 0.8cm;
            }
            
            li {
                margin-bottom: 0.2cm;
            }
            
            hr {
                border: none;
                height: 1px;
                background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
                margin: 0.8cm 0;
            }
            """
            
            html_content = markdown.markdown(report, extensions=['tables', 'fenced_code'])
            
            full_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Git Commit Review Report - {username}</title>
                <style>{css_content}</style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            pdf_filename = f"analysis_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            HTML(string=full_html).write_pdf(pdf_path)
            self.logger.info(f"PDF generated successfully: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            error_msg = f"Error generating PDF with WeasyPrint: {e}"
            self.logger.error(error_msg)
            return None

    def review_repository(self, repo_path: str, commit_count: int = None) -> List[Dict]:
        if commit_count is None:
            commit_count = self.default_commit_count
            
        self.logger.info(f"Reviewing repository: {os.path.basename(repo_path)} (analyzing {commit_count} commits)")
        
        commits = self.get_recent_commits(repo_path, commit_count)
        reviews = []
        
        for i, commit in enumerate(commits, 1):
            diff_content = self.get_commit_diff(repo_path, commit['hash'])
            analysis = self.analyze_commit_with_ai(commit, diff_content)
            reviews.append({
                'repository': repo_path,
                'commit': commit,
                'analysis': analysis
            })
            
        self.logger.info(f"Completed analysis of {len(reviews)} commits from {os.path.basename(repo_path)}")
        return reviews


def get_github_repos(username: str, token: Optional[str] = None) -> List[str]:
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    try:
        url = f"https://api.github.com/users/{username}/repos?per_page=100"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        
        logging.info(f"Found {len(data)} repositories for user {username}")
        
        return [repo['clone_url'] for repo in data]
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching GitHub repositories: {e}"
        logging.error(error_msg)
        return []


def create_output_directory() -> str:
    try:
        output_dir = os.getenv('OUTPUT_DIR', '/Users/yashshah/Desktop/Github_PR_Review')
        
        container_output_dir = os.getenv('CONTAINER_OUTPUT_DIR')
        if container_output_dir and os.path.exists('/app'):
            output_dir = container_output_dir
            
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Using output directory: {output_dir}")
        return output_dir
        
    except (PermissionError, FileNotFoundError, OSError) as e:
        error_msg = f"Cannot create directory in specified location: {e}"
        logging.warning(error_msg)
        
        current_dir = os.getcwd()
        output_dir = os.path.join(current_dir, "Github_PR_Review")
        os.makedirs(output_dir, exist_ok=True)
        
        logging.info(f"Using fallback directory: {output_dir}")
        return output_dir


def get_default_github_username():
    env_username = os.getenv('DEFAULT_GITHUB_USERNAME')
    if env_username:
        return env_username
    
    try:
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, text=True, check=True)
        remote_url = result.stdout.strip()
        
        if 'github.com' in remote_url:
            if remote_url.startswith('https://github.com/'):
                return remote_url.split('/')[3]
            elif remote_url.startswith('git@github.com:'):
                return remote_url.split(':')[1].split('/')[0]
    except:
        pass
    
    try:
        result = subprocess.run(['git', 'config', '--global', 'github.user'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except:
        pass
    
    return None


def main():
    default_commits = int(os.getenv('DEFAULT_COMMIT_COUNT', '5'))
    default_github_token = os.getenv('GITHUB_TOKEN')
    default_github_username = get_default_github_username()
    
    parser = argparse.ArgumentParser(
        description='AI-Powered Git Commit Reviewer (Gemini + GitHub)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--github-username', 
        default=default_github_username,
        help='GitHub username to fetch repos from'
    )
    parser.add_argument(
        '--github-token',
        default=default_github_token,
        help='GitHub Personal Access Token (optional for private repos, can be set via GITHUB_TOKEN env var)'
    )
    parser.add_argument(
        '--commits', '-c', 
        type=int, 
        default=default_commits,
        help=f'Number of recent commits to review per repository (default: {default_commits})'
    )
    parser.add_argument(
        '--output', '-o', 
        help='Output file for the report (if not specified, auto-generated filename will be used)'
    )
    parser.add_argument(
        '--api-key', 
        help='Gemini API key (can be set via GEMINI_API_KEY env var)'
    )
    parser.add_argument(
        '--no-pdf', 
        action='store_true', 
        help='Skip PDF generation'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=os.getenv('LOG_LEVEL', 'INFO'),
        help='Set logging level'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually running analysis'
    )
    
    args = parser.parse_args()

    if not args.github_username:
        print("Error: No GitHub username specified!")
        print("Set DEFAULT_GITHUB_USERNAME in .env or use --github-username")
        sys.exit(1)

    if args.log_level != os.getenv('LOG_LEVEL', 'INFO'):
        os.environ['LOG_LEVEL'] = args.log_level

    reviewer = GitCommitReviewer(api_key=args.api_key)
    
    if args.dry_run:
        print("DRY RUN MODE - No actual analysis will be performed")
        return

    all_reviews = []

    repos = get_github_repos(args.github_username, args.github_token)
    if not repos:
        print("No repositories found on GitHub.")
        reviewer.logger.error("No repositories found")
        sys.exit(1)

    reviewer.logger.info(f"Found {len(repos)} repositories for user {args.github_username}")

    temp_dir = tempfile.mkdtemp()
    reviewer.logger.info(f"Created temporary directory: {temp_dir}")
    
    try:
        for i, clone_url in enumerate(repos, 1):
            repo_name = clone_url.split('/')[-1].replace('.git', '')
            repo_path = os.path.join(temp_dir, repo_name)
            reviewer.logger.info(f"Processing repository {i}/{len(repos)}: {repo_name}")
            
            success = reviewer.clone_repository_with_auth(clone_url, repo_path, args.github_token)
            if not success:
                continue
                
            reviews = reviewer.review_repository(repo_path, args.commits)
            all_reviews.extend(reviews)
                
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        reviewer.logger.info(f"Cleaned up temporary directory: {temp_dir}")

    if not all_reviews:
        print("No commits were analyzed.")
        reviewer.logger.warning("No commits were analyzed")
        sys.exit(1)

    total_commits = len(all_reviews)
    total_repos = len(set(r['repository'] for r in all_reviews))
    
    reviewer.logger.info(f"Analysis complete: {total_commits} commits from {total_repos} repositories")
    
    scores = [r['analysis']['score'] for r in all_reviews if r['analysis']['score'].isdigit()]
    if scores:
        avg_score = sum(int(s) for s in scores) / len(scores)
        print(f"Average quality score: {avg_score:.1f}/10")
    
    output_dir = create_output_directory()
    
    if args.output:
        if os.path.isabs(args.output):
            output_file = args.output
        else:
            output_file = os.path.join(output_dir, args.output)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f"commit_review_{args.github_username}_{timestamp}.txt")

    report = reviewer.generate_report(all_reviews, output_file)
    
    if not args.no_pdf:
        reviewer.logger.info("Starting PDF generation")
        
        try:
            pdf_generated = False
            
            if PDF_AVAILABLE:
                try:
                    pdf_path = reviewer.generate_enhanced_pdf_with_weasyprint(report, output_dir, args.github_username)
                    if pdf_path:
                        print(f"Enhanced PDF saved to: {os.path.abspath(pdf_path)}")
                        pdf_generated = True
                except Exception as e:
                    reviewer.logger.warning(f"WeasyPrint PDF generation failed: {e}")
            
            if not pdf_generated and REPORTLAB_AVAILABLE:
                try:
                    pdf_path = reviewer.generate_pdf_with_reportlab(all_reviews, output_dir, args.github_username)
                    if pdf_path:
                        print(f"Enhanced PDF saved to: {os.path.abspath(pdf_path)}")
                        pdf_generated = True
                except Exception as e:
                    reviewer.logger.warning(f"ReportLab PDF generation failed: {e}")
            
            if not pdf_generated:
                print("PDF generation failed. Install dependencies with:")
                print("pip install weasyprint markdown")
                print("or")
                print("pip install reportlab")
                reviewer.logger.warning("PDF generation failed - missing dependencies")
                
        except Exception as e:
            error_msg = f"PDF generation error: {e}"
            reviewer.logger.error(error_msg)

    print(f"Analysis complete!")
    print(f"All files saved to: {output_dir}")
    print(f"Text report: {os.path.basename(output_file)}")
    if not args.no_pdf:
        print(f"PDF with professional typography generated!")
    
    print(f"Log file: {os.getenv('LOG_FILE', 'app.log')}")
    reviewer.logger.info("Application completed successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Analysis interrupted by user")
        logging.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logging.error(error_msg, exc_info=True)
        print(f"Error: {error_msg}")
        print("Check the log file for detailed error information.")
        sys.exit(1)