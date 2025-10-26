"""
Repository cloning functionality with parallel processing
"""
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from github.Repository import Repository
import git
# Import settings with fallback
try:
    from config.settings import REPOS_DIR, MAX_CONCURRENT_REPOS, CLONE_TIMEOUT
except ImportError:
    REPOS_DIR = Path("data/repos")
    MAX_CONCURRENT_REPOS = 4
    CLONE_TIMEOUT = 300

logger = logging.getLogger(__name__)

class RepositoryCloner:
    """Handles cloning of GitHub repositories with parallel processing"""
    
    def __init__(self, base_dir: Path = REPOS_DIR):
        """
        Initialize repository cloner
        
        Args:
            base_dir: Base directory to store cloned repositories
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cloned_repos = []
        self.failed_repos = []
    
    def clone_repository(self, repo: Repository, include_private: bool = False) -> Optional[Dict]:
        """
        Clone a single repository
        
        Args:
            repo: GitHub Repository object
            include_private: Whether to include private repositories
            
        Returns:
            Dictionary with clone information or None if failed
        """
        try:
            # Skip private repositories if not including them
            if repo.private and not include_private:
                logger.info(f"Skipping private repository: {repo.full_name}")
                return None
            
            # Create repository directory
            repo_dir = self.base_dir / repo.name
            if repo_dir.exists():
                logger.info(f"Repository {repo.name} already exists, skipping clone")
                return {
                    'name': repo.name,
                    'full_name': repo.full_name,
                    'path': str(repo_dir),
                    'url': repo.clone_url,
                    'private': repo.private,
                    'size': repo.size,
                    'language': repo.language,
                    'clone_url': repo.clone_url,
                    'ssh_url': repo.ssh_url,
                    'status': 'already_exists'
                }
            
            # Clone the repository
            logger.info(f"Cloning repository: {repo.full_name}")
            
            # Use HTTPS URL for cloning
            clone_url = repo.clone_url
            if repo.private and include_private:
                # For private repos, we might need authentication
                # This would require setting up SSH keys or using token-based auth
                logger.warning(f"Private repository {repo.full_name} may require authentication")
            
            # Clone with timeout
            git_repo = git.Repo.clone_from(
                clone_url,
                repo_dir,
                timeout=CLONE_TIMEOUT,
                progress=None  # Disable progress to avoid issues in non-interactive mode
            )
            
            # Get repository metadata
            repo_info = {
                'name': repo.name,
                'full_name': repo.full_name,
                'path': str(repo_dir),
                'url': repo.html_url,
                'private': repo.private,
                'size': repo.size,
                'language': repo.language,
                'clone_url': repo.clone_url,
                'ssh_url': repo.ssh_url,
                'default_branch': repo.default_branch,
                'created_at': repo.created_at.isoformat() if repo.created_at else None,
                'updated_at': repo.updated_at.isoformat() if repo.updated_at else None,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'open_issues': repo.open_issues_count,
                'status': 'cloned'
            }
            
            logger.info(f"Successfully cloned repository: {repo.full_name}")
            return repo_info
            
        except git.exc.GitCommandError as e:
            logger.error(f"Git error cloning {repo.full_name}: {e}")
            self.failed_repos.append({
                'name': repo.name,
                'full_name': repo.full_name,
                'error': str(e),
                'status': 'git_error'
            })
            return None
        except Exception as e:
            logger.error(f"Unexpected error cloning {repo.full_name}: {e}")
            self.failed_repos.append({
                'name': repo.name,
                'full_name': repo.full_name,
                'error': str(e),
                'status': 'error'
            })
            return None
    
    def clone_repositories_parallel(self, repos: List[Repository], include_private: bool = False, max_workers: int = MAX_CONCURRENT_REPOS) -> List[Dict]:
        """
        Clone multiple repositories in parallel
        
        Args:
            repos: List of GitHub Repository objects
            include_private: Whether to include private repositories
            max_workers: Maximum number of concurrent clone operations
            
        Returns:
            List of repository information dictionaries
        """
        logger.info(f"Starting parallel clone of {len(repos)} repositories with {max_workers} workers")
        
        self.cloned_repos = []
        self.failed_repos = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all clone tasks
            future_to_repo = {
                executor.submit(self.clone_repository, repo, include_private): repo
                for repo in repos
            }
            
            # Process completed tasks
            for future in as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result()
                    if result:
                        self.cloned_repos.append(result)
                except Exception as e:
                    logger.error(f"Exception during cloning of {repo.full_name}: {e}")
                    self.failed_repos.append({
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'error': str(e),
                        'status': 'exception'
                    })
        
        logger.info(f"Clone completed: {len(self.cloned_repos)} successful, {len(self.failed_repos)} failed")
        return self.cloned_repos
    
    def get_repository_path(self, repo_name: str) -> Optional[Path]:
        """
        Get the local path of a cloned repository
        
        Args:
            repo_name: Name of the repository
            
        Returns:
            Path to the repository or None if not found
        """
        repo_path = self.base_dir / repo_name
        return repo_path if repo_path.exists() else None
    
    def cleanup_repository(self, repo_name: str) -> bool:
        """
        Remove a cloned repository from local storage
        
        Args:
            repo_name: Name of the repository to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            repo_path = self.base_dir / repo_name
            if repo_path.exists():
                shutil.rmtree(repo_path)
                logger.info(f"Cleaned up repository: {repo_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up repository {repo_name}: {e}")
            return False
    
    def cleanup_all_repositories(self) -> int:
        """
        Remove all cloned repositories from local storage
        
        Returns:
            Number of repositories cleaned up
        """
        cleaned_count = 0
        try:
            if self.base_dir.exists():
                for item in self.base_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item)
                        cleaned_count += 1
                logger.info(f"Cleaned up {cleaned_count} repositories")
        except Exception as e:
            logger.error(f"Error cleaning up all repositories: {e}")
        
        return cleaned_count
    
    def get_clone_statistics(self) -> Dict:
        """
        Get statistics about cloned repositories
        
        Returns:
            Dictionary with clone statistics
        """
        total_size = 0
        languages = {}
        private_count = 0
        
        for repo_info in self.cloned_repos:
            if repo_info.get('size'):
                total_size += repo_info['size']
            
            if repo_info.get('private'):
                private_count += 1
            
            language = repo_info.get('language')
            if language:
                languages[language] = languages.get(language, 0) + 1
        
        return {
            'total_repositories': len(self.cloned_repos),
            'failed_repositories': len(self.failed_repos),
            'total_size_kb': total_size,
            'total_size_mb': round(total_size / 1024, 2),
            'private_repositories': private_count,
            'languages': languages,
            'success_rate': len(self.cloned_repos) / (len(self.cloned_repos) + len(self.failed_repos)) * 100 if (len(self.cloned_repos) + len(self.failed_repos)) > 0 else 0
        }
