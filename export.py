import os
import requests
import base64
from datetime import datetime

class GitHubExporter:
    def __init__(self, token, owner, repo):
        """
        Initialize the exporter with GitHub credentials and repository info.
        
        Args:
            token (str): GitHub personal access token
            owner (str): Repository owner username
            repo (str): Repository name
        """
        self.headers = {'Authorization': f'token {token}'}
        self.owner = owner
        self.repo = repo
        self.base_url = f'https://api.github.com/repos/{owner}/{repo}'

    def get_files(self):
        """Get all files and their content from the repository."""
        response = requests.get(f'{self.base_url}/git/trees/main?recursive=1', headers=self.headers)
        if response.status_code != 200:
            response = requests.get(f'{self.base_url}/git/trees/master?recursive=1', headers=self.headers)
        
        files_content = []
        if response.status_code == 200:
            tree = response.json().get('tree', [])
            for item in tree:
                if item['type'] == 'blob':
                    file_response = requests.get(item['url'], headers=self.headers)
                    if file_response.status_code == 200:
                        content = base64.b64decode(file_response.json()['content']).decode('utf-8', errors='ignore')
                        files_content.append(f"\n=== File: {item['path']} ===\n{content}")
        
        return '\n'.join(files_content)

    def get_issues(self):
        """Get all issues from the repository."""
        issues = []
        page = 1
        while True:
            response = requests.get(
                f'{self.base_url}/issues',
                headers=self.headers,
                params={'state': 'all', 'page': page, 'per_page': 100}
            )
            if response.status_code != 200 or not response.json():
                break
            
            for issue in response.json():
                issue_text = f"\n=== Issue #{issue['number']}: {issue['title']} ===\n"
                issue_text += f"State: {issue['state']}\n"
                issue_text += f"Created: {issue['created_at']}\n"
                issue_text += f"Description:\n{issue['body']}\n"
                
                # Get comments for each issue
                comments_response = requests.get(issue['comments_url'], headers=self.headers)
                if comments_response.status_code == 200:
                    for comment in comments_response.json():
                        issue_text += f"\nComment by {comment['user']['login']} on {comment['created_at']}:\n"
                        issue_text += f"{comment['body']}\n"
                
                issues.append(issue_text)
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
        
        content = []
        
        # Repository information
        repo_info = requests.get(self.base_url, headers=self.headers).json()
        content.append(f"=== Repository: {repo_info['full_name']} ===")
        content.append(f"Description: {repo_info['description']}")
        content.append(f"Created: {repo_info['created_at']}")
        content.append(f"Last Updated: {repo_info['updated_at']}")
        content.append(f"Default Branch: {repo_info['default_branch']}")
        content.append("\n=== Files ===")
        content.append(self.get_files())
        content.append("\n=== Issues ===")
        content.append(self.get_issues())
        content.append("\n=== Pull Requests ===")
        content.append(self.get_pull_requests())
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        return output_file

# Example usage
if __name__ == "__main__":
    # Replace these with your values
    TOKEN = "your_github_personal_access_token"
    OWNER = "repository_owner_username"
    REPO = "repository_name"
    
    exporter = GitHubExporter(TOKEN, OWNER, REPO)
    output_file = exporter.export_to_file()
    print(f"Repository exported to: {output_file}")
