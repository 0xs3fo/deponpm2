"""
Configuration settings for the Bug Bounty Package Analyzer
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
REPOS_DIR = DATA_DIR / "repos"
RESULTS_DIR = DATA_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"

# Create directories if they don't exist
for directory in [DATA_DIR, REPOS_DIR, RESULTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# GitHub API settings
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RATE_LIMIT = 5000  # Requests per hour for authenticated users
GITHUB_RATE_LIMIT_UNAUTH = 60  # Requests per hour for unauthenticated users

# NPM Registry settings
NPM_REGISTRY_BASE = "https://registry.npmjs.org"
NPM_RATE_LIMIT = 1000  # Conservative rate limit

# Processing settings
MAX_CONCURRENT_REPOS = 4
MAX_CONCURRENT_COMMITS = 8
MAX_CONCURRENT_NPM_CHECKS = 10

# Timeout settings (in seconds)
API_TIMEOUT = 30
CLONE_TIMEOUT = 300
REQUEST_TIMEOUT = 10

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
BACKOFF_FACTOR = 2

# Supported package managers
PACKAGE_MANAGERS = {
    'npm': ['package.json'],
    'yarn': ['yarn.lock', 'package.json'],
    'pip': ['requirements.txt', 'setup.py', 'pyproject.toml'],
    'maven': ['pom.xml'],
    'gradle': ['build.gradle', 'build.gradle.kts'],
    'composer': ['composer.json'],
    'cargo': ['Cargo.toml'],
    'go': ['go.mod', 'go.sum'],
    'ruby': ['Gemfile', 'Gemfile.lock'],
    'nuget': ['packages.config', '*.csproj', '*.vbproj']
}

# File patterns to search for packages
PACKAGE_FILE_PATTERNS = [
    '**/package.json',
    '**/requirements.txt',
    '**/setup.py',
    '**/pyproject.toml',
    '**/pom.xml',
    '**/build.gradle',
    '**/build.gradle.kts',
    '**/composer.json',
    '**/Cargo.toml',
    '**/go.mod',
    '**/go.sum',
    '**/Gemfile',
    '**/packages.config',
    '**/*.csproj',
    '**/*.vbproj'
]

# Output formats
SUPPORTED_OUTPUT_FORMATS = ['json', 'csv', 'html', 'txt']

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = LOGS_DIR / 'bug_bounty_analyzer.log'
