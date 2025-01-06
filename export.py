import os
import requests
import base64
from datetime import datetime
from tqdm import tqdm
from halo import Halo
import argparse

class GitHubExporter:
    def __init__(self, token, owner, repo):
        """
        Initialize the exporter with GitHub credentials and repository info.
        
        Args:
            token (str): GitHub personal access token
            owner (str): Repository owner username
            repo (str): Repository name
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'token {token}'})
        self.owner = owner
        self.repo = repo
        self.base_url = f'https://api.github.com/repos/{owner}/{repo}'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def get_files(self):
        """Get all files and their content from the repository, excluding media files."""
        spinner = Halo(text='Fetching repository tree...', spinner='dots')
        spinner.start()
        
        default_branch = self.repo_info['default_branch']
        response = requests.get(f'{self.base_url}/git/trees/{default_branch}?recursive=1', headers=self.headers)
        if response.status_code != 200:
            response = requests.get(f'{self.base_url}/git/trees/master?recursive=1', headers=self.headers)
            if response.status_code != 200:
                spinner.fail('Failed to fetch repository tree')
                raise Exception(f"Failed to fetch repository tree: {response.status_code}")
        
        spinner.succeed('Repository tree fetched successfully')
        
        # Define media file extensions to skip
        media_extensions = {
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', '.ico',
            # Videos
            '.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm', '.mkv', '.m4v',
            # Other binary files
            '.pdf', '.zip', '.tar', '.gz', '.rar'
        }
        
        files_content = []
        tree = response.json().get('tree', [])
        
        # Filter only blob items that aren't media files
        files_to_process = [
            item for item in tree 
            if item['type'] == 'blob' and 
            os.path.splitext(item['path'].lower())[1] not in media_extensions
        ]
        
        with tqdm(total=len(files_to_process), desc="Fetching files") as pbar:
            for item in files_to_process:
                try:
                    file_response = requests.get(item['url'], headers=self.headers)
                    file_response.raise_for_status()
                    content = base64.b64decode(file_response.json()['content']).decode('utf-8', errors='ignore')
                    files_content.append(f"\n=== File: {item['path']} ===\n{content}")
                    if item.get('size', 0) > 1024 * 1024:  # Files larger than 1MB
                        tqdm.write(f"Warning: Large file {item['path']} ({item['size']} bytes)")
                except Exception as e:
                    tqdm.write(f"Error fetching file {item['path']}: {str(e)}")
                    continue
                pbar.update(1)
        
        return '\n'.join(files_content)

    def get_issues(self):
        """Get all issues from the repository."""
        spinner = Halo(text='Fetching issues...', spinner='dots')
        spinner.start()
        
        issues = []
        page = 1
        total_issues = 0
        
        # First, get total number of issues
        response = requests.get(
            f'{self.base_url}/issues',
            headers=self.headers,
            params={'state': 'all', 'page': 1, 'per_page': 1}
        )
        if 'Link' in response.headers:
            # Extract total pages from Link header
            last_link = [l for l in response.headers['Link'].split(', ') if 'rel="last"' in l]
            if last_link:
                total_issues = int(last_link[0].split('page=')[1].split('&')[0])
        
        spinner.stop()
        
        with tqdm(total=total_issues or None, desc="Fetching issues") as pbar:
            while True:
                response = requests.get(
                    f'{self.base_url}/issues',
                    headers=self.headers,
                    params={'state': 'all', 'page': page, 'per_page': 100}
                )
                if response.status_code != 200 or not response.json():
                    break
                
                current_issues = response.json()
                for issue in current_issues:
                    issue_text = f"\n=== Issue #{issue['number']}: {issue['title']} ===\n"
                    issue_text += f"State: {issue['state']}\n"
                    issue_text += f"Created: {issue['created_at']}\n"
                    issue_text += f"Description:\n{issue['body']}\n"
                    
                    # Get comments count
                    comments_count = issue.get('comments', 0)
                    if comments_count > 0:
                        comments_response = requests.get(issue['comments_url'], headers=self.headers)
                        if comments_response.status_code == 200:
                            comments = comments_response.json()
                            with tqdm(total=len(comments), 
                                    desc=f"Fetching comments for issue #{issue['number']}", 
                                    leave=False) as comment_pbar:
                                for comment in comments:
                                    issue_text += f"\nComment by {comment['user']['login']} on {comment['created_at']}:\n"
                                    issue_text += f"{comment['body']}\n"
                                    comment_pbar.update(1)
                    
                    issues.append(issue_text)
                    pbar.update(1)
                
                page += 1
        
        return '\n'.join(issues)

    def get_pull_requests(self):
        """Get all pull requests from the repository."""
        response = requests.get(
            f'{self.base_url}/pulls',
            headers=self.headers,
            params={'state': 'all'}
        )
        
        prs = []
        if response.status_code == 200:
            for pr in response.json():
                pr_text = f"\n=== Pull Request #{pr['number']}: {pr['title']} ===\n"
                pr_text += f"State: {pr['state']}\n"
                pr_text += f"Created: {pr['created_at']}\n"
                pr_text += f"Description:\n{pr['body']}\n"
                prs.append(pr_text)
        
        return '\n'.join(prs)

    def get_project_data(self):
        """Get all project data from the repository's associated projects."""
        spinner = Halo(text='Fetching projects...', spinner='dots')
        spinner.start()
        
        projects_content = []
        
        # Try fetching classic projects
        classic_response = requests.get(
            f'{self.base_url}/projects',
            headers={**self.headers, 'Accept': 'application/vnd.github.inertia-preview+json'}
        )
        
        # Try fetching new GitHub Projects (beta)
        org_projects_response = requests.get(
            f'https://api.github.com/orgs/{self.owner}/projects',
            headers={**self.headers, 'Accept': 'application/vnd.github.project-beta+json'}
        )
        
        if classic_response.status_code != 200 and org_projects_response.status_code != 200:
            spinner.fail('Failed to fetch projects')
            return "No projects found or access denied"
        
        # Handle classic projects
        classic_projects = classic_response.json() if classic_response.status_code == 200 else []
        
        # Handle new projects
        org_projects = org_projects_response.json() if org_projects_response.status_code == 200 else []
        
        if not classic_projects and not org_projects:
            spinner.succeed('No projects found')
            return "No projects found"
        
        spinner.succeed(f'Found {len(classic_projects) + len(org_projects)} projects')
        
        # Process classic projects
        for project in tqdm(classic_projects, desc="Fetching classic project details"):
            project_text = f"\n=== Classic Project: {project['name']} ===\n"
            project_text += f"State: {project['state']}\n"
            project_text += f"Created: {project['created_at']}\n"
            project_text += f"Description: {project.get('body', 'No description')}\n"
            
            # Get columns
            columns_response = requests.get(
                project['columns_url'],
                headers={**self.headers, 'Accept': 'application/vnd.github.inertia-preview+json'}
            )
            
            if columns_response.status_code == 200:
                columns = columns_response.json()
                for column in columns:
                    project_text += f"\n--- Column: {column['name']} ---\n"
                    
                    # Get cards in column
                    cards_response = requests.get(
                        column['cards_url'],
                        headers={**self.headers, 'Accept': 'application/vnd.github.inertia-preview+json'}
                    )
                    
                    if cards_response.status_code == 200:
                        cards = cards_response.json()
                        for card in cards:
                            if card.get('note'):
                                project_text += f"Note: {card['note']}\n"
                            elif card.get('content_url'):
                                content_response = requests.get(
                                    card['content_url'],
                                    headers=self.headers
                                )
                                if content_response.status_code == 200:
                                    content = content_response.json()
                                    project_text += f"Linked {content.get('type', 'item')}: {content.get('title', 'Untitled')}\n"
                            project_text += "---\n"
            
            projects_content.append(project_text)
        
        # Process new projects
        for project in tqdm(org_projects, desc="Fetching new project details"):
            project_text = f"\n=== Project (Beta): {project['title']} ===\n"
            project_text += f"Number: {project['number']}\n"
            project_text += f"Created: {project['created_at']}\n"
            project_text += f"Description: {project.get('body', 'No description')}\n"
            
            # Get project items
            items_response = requests.get(
                f"https://api.github.com/projects/{project['number']}/items",
                headers={**self.headers, 'Accept': 'application/vnd.github.project-beta+json'}
            )
            
            if items_response.status_code == 200:
                items = items_response.json()
                project_text += "\n--- Project Items ---\n"
                for item in items:
                    project_text += f"Title: {item.get('title', 'Untitled')}\n"
                    if 'content' in item:
                        project_text += f"Type: {item['content'].get('type', 'Unknown')}\n"
                    project_text += "---\n"
            
            projects_content.append(project_text)
        
        return '\n'.join(projects_content)

    def export_to_file(self, output_file=None):
        """
        Export all repository data to a text file.
        
        Args:
            output_file (str, optional): Output file path. If not provided,
                                       generates a filename based on repository name and date.
        """
        if not output_file:
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"{self.owner}_{self.repo}_export_{date_str}.txt"
        
        spinner = Halo(text='Initializing export...', spinner='dots')
        spinner.start()
        
        content = []
        
        # Repository information
        response = requests.get(self.base_url, headers=self.headers)
        if response.status_code != 200:
            spinner.fail('Failed to fetch repository info')
            raise Exception(f"Failed to fetch repository info. Status code: {response.status_code}")
        
        repo_info = response.json()
        if not repo_info:
            spinner.fail('Empty response from GitHub API')
            raise Exception("Empty response from GitHub API")
        
        spinner.succeed('Repository info fetched successfully')
        
        content.append(f"=== Repository: {self.owner}/{self.repo} ===")
        content.append(f"Description: {repo_info.get('description', 'No description')}")
        content.append(f"Created: {repo_info.get('created_at', 'Unknown')}")
        content.append(f"Last Updated: {repo_info.get('updated_at', 'Unknown')}")
        content.append(f"Default Branch: {repo_info.get('default_branch', 'Unknown')}")
        
        # Store repo_info as instance variable for other methods to use
        self.repo_info = repo_info
        
        content.append("\n=== Files ===")
        content.append(self.get_files())
        content.append("\n=== Issues ===")
        content.append(self.get_issues())
        content.append("\n=== Pull Requests ===")
        content.append(self.get_pull_requests())
        
        # Add Projects section
        content.append("\n=== Projects ===")
        content.append(self.get_project_data())
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        return output_file

    def _check_rate_limit(self):
        """Check GitHub API rate limit status."""
        response = requests.get('https://api.github.com/rate_limit', headers=self.headers)
        if response.status_code == 200:
            rate_limit = response.json()['resources']['core']
            if rate_limit['remaining'] == 0:
                reset_time = datetime.fromtimestamp(rate_limit['reset'])
                raise Exception(f"API rate limit exceeded. Resets at {reset_time}")

# Example usage
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Export GitHub repository content')
    parser.add_argument('owner', help='Repository owner username')
    parser.add_argument('repo', help='Repository name')
    parser.add_argument('--token', help='GitHub personal access token (alternatively, set GITHUB_TOKEN env variable)')
    parser.add_argument('--output-dir', '-o', default='.',
                       help='Output directory for the export file (default: current directory)')
    
    args = parser.parse_args()
    
    # Get token from args or environment variable
    token = args.token or os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GitHub token must be provided either via --token argument or GITHUB_TOKEN environment variable")
    
    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Generate output path
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(args.output_dir, f"{args.owner}_{args.repo}_export_{date_str}.txt")
    
    exporter = GitHubExporter(token, args.owner, args.repo)
    output_file = exporter.export_to_file(output_file)
    print(f"\nRepository exported to: {output_file}")
