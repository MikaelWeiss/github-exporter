# GitHub Repository Exporter

A Python script that creates a comprehensive export of a GitHub repository's contents, including:
- All repository files and their contents
- Complete issue history with comments
- All pull requests
- Repository metadata

This tool is particularly useful for:
- Creating offline backups of your GitHub repositories
- Migrating repository data to other systems
- Archiving projects
- Generating documentation

## Features

- Exports all repository files with their contents
- Captures full issue history including comments
- Includes all pull requests
- Saves repository metadata (creation date, description, etc.)
- Automatically handles pagination for large repositories
- Supports both main and master branches
- UTF-8 encoding support

## Prerequisites

- Python 3.6 or higher
- GitHub Personal Access Token
- Required Python packages:
  - requests
  - tqdm
  - halo

## Installation

1. Clone this repository:
```
git clone https://github.com/mikaelweiss/github-repo-exporter.git
cd github-repo-exporter
```

2. Create and activate a virtual environment:

On Windows:
```
python -m venv venv
.\venv\Scripts\activate
```

On macOS/Linux:
```
python3 -m venv venv
source venv/bin/activate
```

3. Install the required packages:
```
pip install requests tqdm halo
```

4. Create a GitHub Personal Access Token:
   - Go to GitHub Settings → Developer Settings → Personal Access Tokens
   - Click "Generate New Token"
   - Select the following scopes:
     - `repo` (Full control of private repositories)
   - Copy the generated token (you won't be able to see it again!)

## Usage

1. Set your GitHub Personal Access Token as an environment variable:

On Windows:
```
set GITHUB_TOKEN=your_github_personal_access_token
```

On macOS/Linux:
```
export GITHUB_TOKEN=your_github_personal_access_token
```

2. Open `export.py` and replace the placeholder values at the bottom of the file:
```
OWNER = "repository_owner_username"
REPO = "repository_name"
```

3. Run the script:
```
python export.py
```

The script will create an export file in the current directory with the format: `owner_repo_export_YYYYMMDD_HHMMSS.txt`

### Using as a Module

## Output Format

The export file contains sections for:
- Repository information (name, description, creation date)
- Files (with full content)
- Issues (including all comments)
- Pull Requests

Each section is clearly marked with `=== Section Name ===` headers.

## Error Handling

The script handles common issues such as:
- Rate limiting
- Missing repositories
- Invalid tokens
- Network errors

If any errors occur, they will be reflected in the script's output.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.