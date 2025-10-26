"""
GitHub API client for interacting with GitHub repositories and organizations
"""
import time
import logging
from typing import List, Dict, Optional, Iterator
from github import Github, GithubException
from github.Repository import Repository
from github.Organization import Organization
from github.PaginatedList import PaginatedList
import requests
# Import settings with fallback
try:
    from config.settings import GITHUB_API_BASE, GITHUB_RATE_LIMIT, GITHUB_RATE_LIMIT_UNAUTH, API_TIMEOUT, MAX_RETRIES, RETRY_DELAY, BACKOFF_FACTOR
except ImportError:
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_RATE_LIMIT = 5000
    GITHUB_RATE_LIMIT_UNAUTH = 60
    API_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    BACKOFF_FACTOR = 2

logger = logging.getLogger(__name__)

class GitHubClient:
    """Client for interacting with GitHub API with rate limiting and error handling"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client
        
        Args:
            token: GitHub personal access token (optional)
        """
        self.token = token
        self.github = Github(token) if token else Github()
        self.rate_limit = GITHUB_RATE_LIMIT if token else GITHUB_RATE_LIMIT_UNAUTH
        self.request_count = 0
        self.last_reset = time.time()
        
    def _handle_rate_limit(self):
        """Handle GitHub API rate limiting"""
        try:
            rate_limit = self.github.get_rate_limit()
            remaining = rate_limit.core.remaining
            reset_time = rate_limit.core.reset
            
            if remaining < 100:  # Conservative threshold
                wait_time = reset_time - time.time() + 60  # Add 1 minute buffer
                if wait_time > 0:
                    logger.warning(f"Rate limit low ({remaining} remaining). Waiting {wait_time:.0f} seconds...")
                    time.sleep(wait_time)
        except Exception as e:
            logger.warning(f"Could not check rate limit: {e}")
    
    def _make_request_with_retry(self, func, *args, **kwargs):
        """Make a request with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                self._handle_rate_limit()
                result = func(*args, **kwargs)
                return result
            except GithubException as e:
                if e.status == 403 and "rate limit" in str(e).lower():
                    logger.warning(f"Rate limit exceeded. Waiting before retry {attempt + 1}/{MAX_RETRIES}")
                    time.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))
                    continue
                elif e.status == 404:
                    logger.warning(f"Resource not found: {e}")
                    return None
                else:
                    logger.error(f"GitHub API error: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))
        
        return None
    
    def get_organization(self, org_name: str) -> Optional[Organization]:
        """
        Get GitHub organization by name
        
        Args:
            org_name: Name of the organization
            
        Returns:
            Organization object or None if not found
        """
        try:
            return self._make_request_with_retry(self.github.get_organization, org_name)
        except Exception as e:
            logger.error(f"Failed to get organization {org_name}: {e}")
            return None
    
    def get_organization_repositories(self, org_name: str, include_private: bool = False) -> List[Repository]:
        """
        Get all repositories for an organization
        
        Args:
            org_name: Name of the organization
            include_private: Whether to include private repositories
            
        Returns:
            List of Repository objects
        """
        try:
            org = self.get_organization(org_name)
            if not org:
                return []
            
            # Get repositories with pagination
            repos = []
            page = 1
            per_page = 100
            
            while True:
                try:
                    # Get repositories for current page
                    repo_list = self._make_request_with_retry(
                        lambda: list(org.get_repos(type='all', sort='updated', page=page, per_page=per_page))
                    )
                    
                    if not repo_list:
                        break
                    
                    # Filter private repositories if needed
                    if not include_private:
                        repo_list = [repo for repo in repo_list if not repo.private]
                    
                    repos.extend(repo_list)
                    
                    # If we got fewer repos than requested, we've reached the end
                    if len(repo_list) < per_page:
                        break
                    
                    page += 1
                    
                    # Safety check to prevent infinite loops
                    if page > 1000:  # Reasonable limit
                        logger.warning(f"Reached page limit (1000) for organization {org_name}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error fetching repositories page {page} for {org_name}: {e}")
                    break
            
            logger.info(f"Found {len(repos)} repositories for organization {org_name}")
            return repos
            
        except Exception as e:
            logger.error(f"Failed to get repositories for organization {org_name}: {e}")
            return []
    
    def get_repository_commits(self, repo: Repository, since: Optional[str] = None) -> List[Dict]:
        """
        Get all commits for a repository
        
        Args:
            repo: Repository object
            since: ISO date string to get commits since (optional)
            
        Returns:
            List of commit dictionaries
        """
        try:
            commits = []
            page = 1
            per_page = 100
            
            while True:
                try:
                    # Get commits for current page
                    commit_list = self._make_request_with_retry(
                        lambda: list(repo.get_commits(since=since, page=page, per_page=per_page))
                    )
                    
                    if not commit_list:
                        break
                    
                    # Convert commits to dictionaries
                    for commit in commit_list:
                        commit_data = {
                            'sha': commit.sha,
                            'message': commit.commit.message,
                            'author': {
                                'name': commit.commit.author.name,
                                'email': commit.commit.author.email,
                                'date': commit.commit.author.date.isoformat()
                            },
                            'committer': {
                                'name': commit.commit.committer.name,
                                'email': commit.commit.committer.email,
                                'date': commit.commit.committer.date.isoformat()
                            },
                            'url': commit.html_url,
                            'files_changed': []
                        }
                        
                        # Get files changed in this commit
                        try:
                            files = self._make_request_with_retry(lambda: list(commit.files))
                            for file in files:
                                commit_data['files_changed'].append({
                                    'filename': file.filename,
                                    'status': file.status,
                                    'additions': file.additions,
                                    'deletions': file.deletions,
                                    'changes': file.changes,
                                    'patch': file.patch if hasattr(file, 'patch') else None
                                })
                        except Exception as e:
                            logger.warning(f"Could not get files for commit {commit.sha}: {e}")
                        
                        commits.append(commit_data)
                    
                    # If we got fewer commits than requested, we've reached the end
                    if len(commit_list) < per_page:
                        break
                    
                    page += 1
                    
                    # Safety check
                    if page > 1000:
                        logger.warning(f"Reached page limit (1000) for commits in {repo.full_name}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error fetching commits page {page} for {repo.full_name}: {e}")
                    break
            
            logger.info(f"Found {len(commits)} commits for repository {repo.full_name}")
            return commits
            
        except Exception as e:
            logger.error(f"Failed to get commits for repository {repo.full_name}: {e}")
            return []
    
    def get_repository_file_content(self, repo: Repository, file_path: str, ref: str = 'main') -> Optional[str]:
        """
        Get file content from repository
        
        Args:
            repo: Repository object
            file_path: Path to the file
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            File content as string or None if not found
        """
        try:
            content = self._make_request_with_retry(
                lambda: repo.get_contents(file_path, ref=ref)
            )
            if content and hasattr(content, 'decoded_content'):
                return content.decoded_content.decode('utf-8')
            return None
        except Exception as e:
            logger.debug(f"Could not get file {file_path} from {repo.full_name}: {e}")
            return None
    
    def search_repositories(self, query: str, language: Optional[str] = None) -> List[Repository]:
        """
        Search for repositories using GitHub search API
        
        Args:
            query: Search query
            language: Programming language filter (optional)
            
        Returns:
            List of Repository objects
        """
        try:
            search_query = query
            if language:
                search_query += f" language:{language}"
            
            results = self._make_request_with_retry(
                lambda: self.github.search_repositories(search_query)
            )
            
            if results:
                return list(results)
            return []
            
        except Exception as e:
            logger.error(f"Failed to search repositories with query '{query}': {e}")
            return []
