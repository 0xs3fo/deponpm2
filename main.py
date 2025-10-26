#!/usr/bin/env python3
"""
Working Bug Bounty Package Analyzer - Handles missing dependencies gracefully
"""
import asyncio
import logging
import sys
import json
import csv
import os
import time
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Dict
import requests

# Try to import GitPython, fallback to subprocess if not available
try:
    import git
    GIT_PYTHON_AVAILABLE = True
except ImportError:
    GIT_PYTHON_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bug_bounty_analyzer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class WorkingGitHubClient:
    """GitHub API client that works without complex dependencies"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({'Authorization': f'token {token}'})
        self.session.headers.update({'Accept': 'application/vnd.github.v3+json'})
        self.rate_limit_remaining = 5000 if token else 60
        self.rate_limit_reset = time.time() + 3600
    
    def _handle_rate_limit(self):
        """Handle rate limiting"""
        if self.rate_limit_remaining < 10:
            wait_time = self.rate_limit_reset - time.time() + 60
            if wait_time > 0:
                logger.warning(f"Rate limit low. Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)
    
    def get_organization_repositories(self, org_name: str, include_private: bool = False) -> List[Dict]:
        """Get repositories for an organization"""
        logger.info(f"Fetching repositories for organization: {org_name}")
        
        repos = []
        page = 1
        per_page = 100
        
        while True:
            self._handle_rate_limit()
            
            url = f"https://api.github.com/orgs/{org_name}/repos"
            params = {
                'type': 'all',
                'sort': 'updated',
                'page': page,
                'per_page': per_page
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                # Update rate limit info
                if 'X-RateLimit-Remaining' in response.headers:
                    self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                if 'X-RateLimit-Reset' in response.headers:
                    self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
                
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        break
                    
                    for repo in data:
                        if not repo.get('private', False) or include_private:
                            repos.append({
                                'name': repo['name'],
                                'full_name': repo['full_name'],
                                'html_url': repo['html_url'],
                                'clone_url': repo['clone_url'],
                                'language': repo.get('language'),
                                'size': repo.get('size', 0),
                                'stars': repo.get('stargazers_count', 0),
                                'forks': repo.get('forks_count', 0),
                                'created_at': repo.get('created_at'),
                                'updated_at': repo.get('updated_at'),
                                'private': repo.get('private', False)
                            })
                    
                    if len(data) < per_page:
                        break
                    
                    page += 1
                    if page > 100:  # Safety limit
                        break
                        
                elif response.status_code == 404:
                    logger.error(f"Organization {org_name} not found")
                    break
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching repositories: {e}")
                break
        
        logger.info(f"Found {len(repos)} repositories")
        return repos
    
    def get_repository_commits(self, repo_full_name: str, since: Optional[str] = None) -> List[Dict]:
        """Get commits for a repository"""
        logger.info(f"Fetching commits for repository: {repo_full_name}")
        
        commits = []
        page = 1
        per_page = 100
        
        while True:
            self._handle_rate_limit()
            
            url = f"https://api.github.com/repos/{repo_full_name}/commits"
            params = {
                'page': page,
                'per_page': per_page
            }
            if since:
                params['since'] = since
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        break
                    
                    for commit in data:
                        commits.append({
                            'sha': commit['sha'],
                            'message': commit['commit']['message'],
                            'author': {
                                'name': commit['commit']['author']['name'],
                                'email': commit['commit']['author']['email'],
                                'date': commit['commit']['author']['date']
                            },
                            'committer': {
                                'name': commit['commit']['committer']['name'],
                                'email': commit['commit']['committer']['email'],
                                'date': commit['commit']['committer']['date']
                            },
                            'url': commit['html_url']
                        })
                    
                    if len(data) < per_page:
                        break
                    
                    page += 1
                    if page > 100:  # Safety limit
                        break
                        
                elif response.status_code == 404:
                    logger.warning(f"Repository {repo_full_name} not found or no access")
                    break
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching commits: {e}")
                break
        
        logger.info(f"Found {len(commits)} commits")
        return commits

class WorkingPackageExtractor:
    """Package extractor that works with local repositories"""
    
    def __init__(self):
        self.package_files = [
            'package.json',
            'requirements.txt',
            'setup.py',
            'pyproject.toml',
            'pom.xml',
            'build.gradle',
            'build.gradle.kts',
            'composer.json',
            'Cargo.toml',
            'go.mod',
            'go.sum',
            'Gemfile',
            'Gemfile.lock',
            'packages.config',
            '*.csproj',
            '*.vbproj'
        ]
    
    def extract_packages_from_local_repo(self, repo_path: str, repo_name: str) -> List[Dict]:
        """Extract packages from a local repository"""
        packages = []
        repo_dir = Path(repo_path)
        
        if not repo_dir.exists():
            logger.warning(f"Repository path does not exist: {repo_path}")
            return packages
        
        logger.info(f"Extracting packages from local repository: {repo_name}")
        
        # Find all package files
        package_files_found = []
        for pattern in self.package_files:
            for file_path in repo_dir.rglob(pattern):
                if file_path.is_file():
                    package_files_found.append(file_path)
        
        # Extract packages from each file
        for file_path in package_files_found:
            try:
                file_packages = self._extract_packages_from_file(file_path, repo_name)
                packages.extend(file_packages)
            except Exception as e:
                logger.error(f"Error extracting packages from {file_path}: {e}")
        
        logger.info(f"Found {len(packages)} packages in {repo_name}")
        return packages
    
    def _extract_packages_from_file(self, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from a single file"""
        packages = []
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if not content:
                return packages
            
            # Determine package manager type
            package_type = self._identify_package_type(file_path.name)
            if not package_type:
                return packages
            
            # Extract packages based on type
            if package_type == 'npm':
                packages = self._extract_npm_packages(content, file_path, repo_name)
            elif package_type == 'pip':
                packages = self._extract_pip_packages(content, file_path, repo_name)
            elif package_type == 'maven':
                packages = self._extract_maven_packages(content, file_path, repo_name)
            elif package_type == 'gradle':
                packages = self._extract_gradle_packages(content, file_path, repo_name)
            elif package_type == 'composer':
                packages = self._extract_composer_packages(content, file_path, repo_name)
            elif package_type == 'cargo':
                packages = self._extract_cargo_packages(content, file_path, repo_name)
            elif package_type == 'go':
                packages = self._extract_go_packages(content, file_path, repo_name)
            elif package_type == 'ruby':
                packages = self._extract_ruby_packages(content, file_path, repo_name)
            elif package_type == 'nuget':
                packages = self._extract_nuget_packages(content, file_path, repo_name)
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
        
        return packages
    
    def _identify_package_type(self, filename: str) -> Optional[str]:
        """Identify package manager type from filename"""
        filename_lower = filename.lower()
        
        if filename_lower == 'package.json':
            return 'npm'
        elif filename_lower == 'yarn.lock':
            return 'yarn'
        elif filename_lower == 'requirements.txt':
            return 'pip'
        elif filename_lower == 'setup.py':
            return 'pip'
        elif filename_lower == 'pyproject.toml':
            return 'pip'
        elif filename_lower == 'pom.xml':
            return 'maven'
        elif filename_lower in ['build.gradle', 'build.gradle.kts']:
            return 'gradle'
        elif filename_lower == 'composer.json':
            return 'composer'
        elif filename_lower == 'cargo.toml':
            return 'cargo'
        elif filename_lower in ['go.mod', 'go.sum']:
            return 'go'
        elif filename_lower in ['gemfile', 'gemfile.lock']:
            return 'ruby'
        elif filename_lower == 'packages.config':
            return 'nuget'
        elif filename_lower.endswith(('.csproj', '.vbproj')):
            return 'nuget'
        
        return None
    
    def _extract_npm_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from package.json"""
        packages = []
        
        try:
            data = json.loads(content)
            
            # Extract main package info
            if 'name' in data:
                packages.append({
                    'name': data['name'],
                    'version': data.get('version', 'unknown'),
                    'type': 'package',
                    'category': 'main',
                    'package_manager': 'npm',
                    'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                    'source': 'package.json',
                    'repo_name': repo_name
                })
            
            # Extract dependencies
            for deps_key in ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']:
                if deps_key in data and isinstance(data[deps_key], dict):
                    for name, version in data[deps_key].items():
                        packages.append({
                            'name': name,
                            'version': version,
                            'type': 'dependency',
                            'category': deps_key,
                            'package_manager': 'npm',
                            'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                            'source': 'package.json',
                            'repo_name': repo_name
                        })
                        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing package.json {file_path}: {e}")
        
        return packages
    
    def _extract_pip_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from requirements.txt, setup.py, or pyproject.toml"""
        packages = []
        
        try:
            if file_path.name == 'requirements.txt':
                packages = self._extract_requirements_txt(content, file_path, repo_name)
            elif file_path.name == 'setup.py':
                packages = self._extract_setup_py(content, file_path, repo_name)
            elif file_path.name == 'pyproject.toml':
                packages = self._extract_pyproject_toml(content, file_path, repo_name)
        except Exception as e:
            logger.error(f"Error extracting pip packages from {file_path}: {e}")
        
        return packages
    
    def _extract_requirements_txt(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from requirements.txt"""
        packages = []
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                # Parse package specification
                name, version = self._parse_pip_specification(line)
                packages.append({
                    'name': name,
                    'version': version,
                    'type': 'dependency',
                    'category': 'requirements',
                    'package_manager': 'pip',
                    'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                    'source': f'requirements.txt:line_{line_num}',
                    'repo_name': repo_name
                })
        
        return packages
    
    def _extract_setup_py(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from setup.py"""
        packages = []
        
        try:
            # Extract install_requires
            import re
            install_requires_match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if install_requires_match:
                deps_text = install_requires_match.group(1)
                deps = re.findall(r'["\']([^"\']+)["\']', deps_text)
                for dep in deps:
                    name, version = self._parse_pip_specification(dep)
                    packages.append({
                        'name': name,
                        'version': version,
                        'type': 'dependency',
                        'category': 'install_requires',
                        'package_manager': 'pip',
                        'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                        'source': 'setup.py:install_requires',
                        'repo_name': repo_name
                    })
            
            # Extract package name and version
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            
            if name_match:
                packages.append({
                    'name': name_match.group(1),
                    'version': version_match.group(1) if version_match else 'unknown',
                    'type': 'package',
                    'category': 'main',
                    'package_manager': 'pip',
                    'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                    'source': 'setup.py:main',
                    'repo_name': repo_name
                })
                
        except Exception as e:
            logger.error(f"Error parsing setup.py {file_path}: {e}")
        
        return packages
    
    def _extract_pyproject_toml(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from pyproject.toml"""
        packages = []
        
        try:
            # This is a simplified implementation
            lines = content.split('\n')
            in_dependencies = False
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if line.startswith('[tool.poetry.dependencies]') or line.startswith('[project.dependencies]'):
                    in_dependencies = True
                    continue
                elif line.startswith('[') and in_dependencies:
                    in_dependencies = False
                    continue
                
                if in_dependencies and '=' in line and not line.startswith('#'):
                    # Parse dependency line
                    if '=' in line:
                        name, version = line.split('=', 1)
                        name = name.strip().strip('"\'')
                        version = version.strip().strip('"\'')
                        
                        packages.append({
                            'name': name,
                            'version': version,
                            'type': 'dependency',
                            'category': 'dependencies',
                            'package_manager': 'pip',
                            'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                            'source': f'pyproject.toml:line_{line_num}',
                            'repo_name': repo_name
                        })
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml {file_path}: {e}")
        
        return packages
    
    def _extract_maven_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from pom.xml"""
        packages = []
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            
            # Extract main artifact info
            group_id = root.find('.//{http://maven.apache.org/POM/4.0.0}groupId')
            artifact_id = root.find('.//{http://maven.apache.org/POM/4.0.0}artifactId')
            version = root.find('.//{http://maven.apache.org/POM/4.0.0}version')
            
            if artifact_id is not None:
                packages.append({
                    'name': f"{group_id.text if group_id is not None else 'unknown'}:{artifact_id.text}",
                    'version': version.text if version is not None else 'unknown',
                    'type': 'package',
                    'category': 'main',
                    'package_manager': 'maven',
                    'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                    'source': 'pom.xml:main',
                    'repo_name': repo_name
                })
            
            # Extract dependencies
            dependencies = root.findall('.//{http://maven.apache.org/POM/4.0.0}dependency')
            for dep in dependencies:
                dep_group_id = dep.find('{http://maven.apache.org/POM/4.0.0}groupId')
                dep_artifact_id = dep.find('{http://maven.apache.org/POM/4.0.0}artifactId')
                dep_version = dep.find('{http://maven.apache.org/POM/4.0.0}version')
                
                if dep_artifact_id is not None:
                    packages.append({
                        'name': f"{dep_group_id.text if dep_group_id is not None else 'unknown'}:{dep_artifact_id.text}",
                        'version': dep_version.text if dep_version is not None else 'unknown',
                        'type': 'dependency',
                        'category': 'dependencies',
                        'package_manager': 'maven',
                        'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                        'source': 'pom.xml:dependencies',
                        'repo_name': repo_name
                    })
                    
        except ET.ParseError as e:
            logger.error(f"Error parsing pom.xml {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error extracting Maven packages from {file_path}: {e}")
        
        return packages
    
    def _extract_gradle_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from build.gradle"""
        packages = []
        
        try:
            import re
            # Look for implementation, compile, testImplementation, etc.
            dependency_patterns = [
                r'(?:implementation|compile|testImplementation|testCompile|api|compileOnly|runtimeOnly)\s+["\']([^"\']+)["\']',
                r'(?:implementation|compile|testImplementation|testCompile|api|compileOnly|runtimeOnly)\s+group:\s*["\']([^"\']+)["\']\s*,\s*name:\s*["\']([^"\']+)["\']\s*,\s*version:\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in dependency_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple):
                        if len(match) == 3:  # group:name:version format
                            group, name, version = match
                            package_name = f"{group}:{name}"
                        else:
                            package_name = match[0]
                            version = 'unknown'
                    else:
                        package_name = match
                        version = 'unknown'
                    
                    packages.append({
                        'name': package_name,
                        'version': version,
                        'type': 'dependency',
                        'category': 'gradle',
                        'package_manager': 'gradle',
                        'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                        'source': 'build.gradle',
                        'repo_name': repo_name
                    })
        except Exception as e:
            logger.error(f"Error extracting Gradle packages from {file_path}: {e}")
        
        return packages
    
    def _extract_composer_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from composer.json"""
        packages = []
        
        try:
            data = json.loads(content)
            
            # Extract main package info
            if 'name' in data:
                packages.append({
                    'name': data['name'],
                    'version': data.get('version', 'unknown'),
                    'type': 'package',
                    'category': 'main',
                    'package_manager': 'composer',
                    'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                    'source': 'composer.json',
                    'repo_name': repo_name
                })
            
            # Extract dependencies
            for deps_key in ['require', 'require-dev']:
                if deps_key in data and isinstance(data[deps_key], dict):
                    for name, version in data[deps_key].items():
                        packages.append({
                            'name': name,
                            'version': version,
                            'type': 'dependency',
                            'category': deps_key,
                            'package_manager': 'composer',
                            'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                            'source': 'composer.json',
                            'repo_name': repo_name
                        })
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing composer.json {file_path}: {e}")
        
        return packages
    
    def _extract_cargo_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from Cargo.toml"""
        packages = []
        
        try:
            # This is a simplified implementation
            lines = content.split('\n')
            in_dependencies = False
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if line.startswith('[dependencies]'):
                    in_dependencies = True
                    continue
                elif line.startswith('[') and in_dependencies:
                    in_dependencies = False
                    continue
                
                if in_dependencies and '=' in line and not line.startswith('#'):
                    name, version = line.split('=', 1)
                    name = name.strip()
                    version = version.strip().strip('"\'')
                    
                    packages.append({
                        'name': name,
                        'version': version,
                        'type': 'dependency',
                        'category': 'dependencies',
                        'package_manager': 'cargo',
                        'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                        'source': f'Cargo.toml:line_{line_num}',
                        'repo_name': repo_name
                    })
        except Exception as e:
            logger.error(f"Error extracting Cargo packages from {file_path}: {e}")
        
        return packages
    
    def _extract_go_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from go.mod"""
        packages = []
        
        try:
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if line.startswith('require ') or line.startswith('replace '):
                    # Parse require or replace directive
                    parts = line.split()
                    if len(parts) >= 2:
                        package_name = parts[1]
                        version = parts[2] if len(parts) > 2 else 'unknown'
                        
                        packages.append({
                            'name': package_name,
                            'version': version,
                            'type': 'dependency',
                            'category': 'require',
                            'package_manager': 'go',
                            'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                            'source': f'go.mod:line_{line_num}',
                            'repo_name': repo_name
                        })
        except Exception as e:
            logger.error(f"Error extracting Go packages from {file_path}: {e}")
        
        return packages
    
    def _extract_ruby_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from Gemfile"""
        packages = []
        
        try:
            import re
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if line.startswith('gem '):
                    # Parse gem directive
                    gem_match = re.match(r'gem\s+["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']+)["\'])?', line)
                    if gem_match:
                        name = gem_match.group(1)
                        version = gem_match.group(2) if gem_match.group(2) else 'unknown'
                        
                        packages.append({
                            'name': name,
                            'version': version,
                            'type': 'dependency',
                            'category': 'gem',
                            'package_manager': 'ruby',
                            'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                            'source': f'Gemfile:line_{line_num}',
                            'repo_name': repo_name
                        })
        except Exception as e:
            logger.error(f"Error extracting Ruby packages from {file_path}: {e}")
        
        return packages
    
    def _extract_nuget_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from packages.config or .csproj"""
        packages = []
        
        try:
            if file_path.name == 'packages.config':
                packages = self._extract_packages_config(content, file_path, repo_name)
            elif file_path.name.endswith(('.csproj', '.vbproj')):
                packages = self._extract_csproj_packages(content, file_path, repo_name)
        except Exception as e:
            logger.error(f"Error extracting NuGet packages from {file_path}: {e}")
        
        return packages
    
    def _extract_packages_config(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from packages.config"""
        packages = []
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            for package in root.findall('package'):
                id_attr = package.get('id')
                version_attr = package.get('version')
                
                if id_attr:
                    packages.append({
                        'name': id_attr,
                        'version': version_attr or 'unknown',
                        'type': 'dependency',
                        'category': 'package',
                        'package_manager': 'nuget',
                        'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                        'source': 'packages.config',
                        'repo_name': repo_name
                    })
        except ET.ParseError as e:
            logger.error(f"Error parsing packages.config {file_path}: {e}")
        
        return packages
    
    def _extract_csproj_packages(self, content: str, file_path: Path, repo_name: str) -> List[Dict]:
        """Extract packages from .csproj files"""
        packages = []
        
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            
            # Look for PackageReference elements
            for package_ref in root.findall('.//PackageReference'):
                include_attr = package_ref.get('Include')
                version_attr = package_ref.get('Version')
                
                if include_attr:
                    packages.append({
                        'name': include_attr,
                        'version': version_attr or 'unknown',
                        'type': 'dependency',
                        'category': 'PackageReference',
                        'package_manager': 'nuget',
                        'file_path': str(file_path.relative_to(Path(file_path).anchor)),
                        'source': '.csproj',
                        'repo_name': repo_name
                    })
        except ET.ParseError as e:
            logger.error(f"Error parsing .csproj {file_path}: {e}")
        
        return packages
    
    def _parse_pip_specification(self, spec: str) -> tuple:
        """Parse pip package specification"""
        spec = spec.strip()
        
        # Handle various version specifiers
        for operator in ['==', '>=', '<=', '>', '<', '~=', '!=']:
            if operator in spec:
                name, version = spec.split(operator, 1)
                return name.strip(), f"{operator}{version.strip()}"
        
        # No version specifier
        return spec, 'unknown'

class WorkingNPMChecker:
    """NPM package checker that works without complex dependencies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.checked_packages = []
        self.vulnerable_packages = []
        self.unclaimed_packages = []
    
    def check_packages(self, packages: List[Dict]) -> List[Dict]:
        """Check packages against NPM registry"""
        logger.info(f"Checking {len(packages)} packages against NPM registry")
        
        checked_packages = []
        npm_packages = [pkg for pkg in packages if pkg.get('package_manager') == 'npm']
        
        for package in npm_packages:
            package_name = package['name']
            logger.info(f"Checking package: {package_name}")
            
            try:
                url = f"https://registry.npmjs.org/{package_name}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    # Package exists
                    updated_package = package.copy()
                    updated_package.update({
                        'npm_status': 'found',
                        'is_unclaimed': False,
                        'is_vulnerable': self._is_potentially_vulnerable(package_name),
                        'last_checked': time.time()
                    })
                    
                    if updated_package['is_vulnerable']:
                        self.vulnerable_packages.append(updated_package)
                    
                elif response.status_code == 404:
                    # Package not found - potentially unclaimed
                    updated_package = package.copy()
                    updated_package.update({
                        'npm_status': 'not_found',
                        'is_unclaimed': True,
                        'is_vulnerable': False,
                        'last_checked': time.time()
                    })
                    self.unclaimed_packages.append(updated_package)
                    
                else:
                    # Other error
                    updated_package = package.copy()
                    updated_package.update({
                        'npm_status': 'error',
                        'is_unclaimed': False,
                        'is_vulnerable': False,
                        'error': f"HTTP {response.status_code}",
                        'last_checked': time.time()
                    })
                
                checked_packages.append(updated_package)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error checking package {package_name}: {e}")
                updated_package = package.copy()
                updated_package.update({
                    'npm_status': 'error',
                    'is_unclaimed': False,
                    'is_vulnerable': False,
                    'error': str(e),
                    'last_checked': time.time()
                })
                checked_packages.append(updated_package)
        
        return checked_packages
    
    def _is_potentially_vulnerable(self, package_name: str) -> bool:
        """Check if package name suggests potential vulnerability"""
        suspicious_patterns = [
            'test', 'demo', 'example', 'sample', 'temp', 'tmp',
            'admin', 'root', 'password', 'secret', 'key', 'token',
            'debug', 'dev', 'development', 'local', 'private'
        ]
        
        package_lower = package_name.lower()
        
        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if pattern in package_lower:
                return True
        
        # Check for very short names (might be typosquatting)
        if len(package_name) < 3:
            return True
        
        return False

class RepositoryCloner:
    """Handles cloning of GitHub repositories to avoid API rate limits"""
    
    def __init__(self, base_dir: str = "cloned_repos"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cloned_repos = []
        self.failed_repos = []
    
    def clone_repository(self, repo_info: Dict, include_private: bool = False) -> Optional[Dict]:
        """Clone a single repository"""
        try:
            repo_name = repo_info['name']
            clone_url = repo_info['clone_url']
            repo_dir = self.base_dir / repo_name
            
            # Skip if already cloned
            if repo_dir.exists():
                logger.info(f"Repository {repo_name} already exists, skipping clone")
                return {
                    **repo_info,
                    'local_path': str(repo_dir),
                    'status': 'already_exists'
                }
            
            # Skip private repositories if not including them
            if repo_info.get('private', False) and not include_private:
                logger.info(f"Skipping private repository: {repo_name}")
                return None
            
            logger.info(f"Cloning repository: {repo_name}")
            
            # Clone using GitPython if available, otherwise subprocess
            if GIT_PYTHON_AVAILABLE:
                git_repo = git.Repo.clone_from(clone_url, repo_dir, progress=None)
            else:
                # Use subprocess as fallback
                result = subprocess.run(
                    ['git', 'clone', clone_url, str(repo_dir)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode != 0:
                    raise Exception(f"Git clone failed: {result.stderr}")
            
            # Get repository metadata
            cloned_repo = {
                **repo_info,
                'local_path': str(repo_dir),
                'status': 'cloned'
            }
            
            logger.info(f"Successfully cloned repository: {repo_name}")
            return cloned_repo
            
        except Exception as e:
            logger.error(f"Error cloning {repo_info.get('name', 'unknown')}: {e}")
            self.failed_repos.append({
                'name': repo_info.get('name', 'unknown'),
                'error': str(e),
                'status': 'clone_failed'
            })
            return None
    
    def clone_repositories(self, repos: List[Dict], include_private: bool = False, max_repos: int = None) -> List[Dict]:
        """Clone multiple repositories"""
        logger.info(f"Starting to clone {len(repos)} repositories")
        
        if max_repos:
            repos = repos[:max_repos]
        
        self.cloned_repos = []
        self.failed_repos = []
        
        for i, repo in enumerate(repos, 1):
            print(f"  [{i}/{len(repos)}] Cloning {repo['name']}...")
            cloned_repo = self.clone_repository(repo, include_private)
            if cloned_repo:
                self.cloned_repos.append(cloned_repo)
        
        logger.info(f"Clone completed: {len(self.cloned_repos)} successful, {len(self.failed_repos)} failed")
        return self.cloned_repos
    
    def get_clone_statistics(self) -> Dict:
        """Get statistics about cloned repositories"""
        return {
            'total_repositories': len(self.cloned_repos),
            'failed_repositories': len(self.failed_repos),
            'success_rate': len(self.cloned_repos) / (len(self.cloned_repos) + len(self.failed_repos)) * 100 if (len(self.cloned_repos) + len(self.failed_repos)) > 0 else 0
        }

class WorkingReporter:
    """Reporter that works without complex dependencies"""
    
    def __init__(self, output_dir: str = "results", org_name: str = None):
        self.base_output_dir = Path(output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create organization-specific folder
        if org_name:
            self.output_dir = self.base_output_dir / org_name
        else:
            self.output_dir = self.base_output_dir
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    def generate_reports(self, analysis_data: Dict) -> Dict[str, Path]:
        """Generate reports in multiple formats"""
        output_files = {}
        
        try:
            # JSON report
            json_file = self.output_dir / f"bug_bounty_analysis_{self.timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            output_files['json'] = json_file
            
            # CSV report
            csv_file = self.output_dir / f"bug_bounty_packages_{self.timestamp}.csv"
            packages = analysis_data.get('packages', [])
            if packages:
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['name', 'version', 'package_manager', 'type', 'is_vulnerable', 'is_unclaimed', 'npm_status'])
                    writer.writeheader()
                    for package in packages:
                        writer.writerow({
                            'name': package.get('name', ''),
                            'version': package.get('version', ''),
                            'package_manager': package.get('package_manager', ''),
                            'type': package.get('type', ''),
                            'is_vulnerable': package.get('is_vulnerable', False),
                            'is_unclaimed': package.get('is_unclaimed', False),
                            'npm_status': package.get('npm_status', '')
                        })
            output_files['csv'] = csv_file
            
            # HTML report
            html_file = self.output_dir / f"bug_bounty_report_{self.timestamp}.html"
            self._generate_html_report(analysis_data, html_file)
            output_files['html'] = html_file
            
            # Text report
            txt_file = self.output_dir / f"bug_bounty_report_{self.timestamp}.txt"
            self._generate_text_report(analysis_data, txt_file)
            output_files['txt'] = txt_file
            
            logger.info(f"Reports generated in {self.output_dir}")
            return output_files
            
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
            return {}
    
    def _generate_html_report(self, analysis_data: Dict, output_file: Path):
        """Generate HTML report"""
        packages = analysis_data.get('packages', [])
        vulnerable = [pkg for pkg in packages if pkg.get('is_vulnerable', False)]
        unclaimed = [pkg for pkg in packages if pkg.get('is_unclaimed', False)]
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Bug Bounty Package Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }}
        .vulnerable {{ background-color: #fff5f5; }}
        .unclaimed {{ background-color: #fffbf0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Bug Bounty Package Analysis Report</h1>
        <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <div class="stat-card">
            <h3>{len(analysis_data.get('repositories', []))}</h3>
            <p>Repositories</p>
        </div>
        <div class="stat-card">
            <h3>{len(packages)}</h3>
            <p>Total Packages</p>
        </div>
        <div class="stat-card">
            <h3 style="color: red;">{len(vulnerable)}</h3>
            <p>Vulnerable Packages</p>
        </div>
        <div class="stat-card">
            <h3 style="color: orange;">{len(unclaimed)}</h3>
            <p>Unclaimed Packages</p>
        </div>
    </div>
    
    <h2>Vulnerable Packages</h2>
    {self._create_package_table(vulnerable, 'vulnerable')}
    
    <h2>Unclaimed Packages</h2>
    {self._create_package_table(unclaimed, 'unclaimed')}
    
    <h2>All Packages</h2>
    {self._create_package_table(packages, '')}
</body>
</html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _create_package_table(self, packages: List[Dict], table_class: str) -> str:
        """Create HTML table for packages"""
        if not packages:
            return "<p>No packages found.</p>"
        
        html = f'<table class="{table_class}">'
        html += '<tr><th>Name</th><th>Version</th><th>Manager</th><th>Type</th><th>Status</th></tr>'
        
        for package in packages:
            status = []
            if package.get('is_vulnerable'):
                status.append('Vulnerable')
            if package.get('is_unclaimed'):
                status.append('Unclaimed')
            if not status:
                status.append('Safe')
            
            html += f'''
            <tr>
                <td>{package.get('name', 'Unknown')}</td>
                <td>{package.get('version', 'Unknown')}</td>
                <td>{package.get('package_manager', 'Unknown')}</td>
                <td>{package.get('type', 'Unknown')}</td>
                <td>{', '.join(status)}</td>
            </tr>
            '''
        
        html += '</table>'
        return html
    
    def _generate_text_report(self, analysis_data: Dict, output_file: Path):
        """Generate text report"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Bug Bounty Package Analysis Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            repos = analysis_data.get('repositories', [])
            packages = analysis_data.get('packages', [])
            
            f.write(f"Repositories analyzed: {len(repos)}\n")
            f.write(f"Total packages found: {len(packages)}\n")
            
            vulnerable = [pkg for pkg in packages if pkg.get('is_vulnerable', False)]
            unclaimed = [pkg for pkg in packages if pkg.get('is_unclaimed', False)]
            
            f.write(f"Vulnerable packages: {len(vulnerable)}\n")
            f.write(f"Unclaimed packages: {len(unclaimed)}\n\n")
            
            if vulnerable:
                f.write("VULNERABLE PACKAGES:\n")
                f.write("-" * 30 + "\n")
                for pkg in vulnerable:
                    f.write(f"- {pkg.get('name', 'Unknown')} ({pkg.get('package_manager', 'Unknown')})\n")
                f.write("\n")
            
            if unclaimed:
                f.write("UNCLAIMED PACKAGES:\n")
                f.write("-" * 30 + "\n")
                for pkg in unclaimed:
                    f.write(f"- {pkg.get('name', 'Unknown')} ({pkg.get('package_manager', 'Unknown')})\n")
                f.write("\n")
            
            if packages:
                f.write("ALL PACKAGES:\n")
                f.write("-" * 30 + "\n")
                for pkg in packages:
                    status = []
                    if pkg.get('is_vulnerable'):
                        status.append('Vulnerable')
                    if pkg.get('is_unclaimed'):
                        status.append('Unclaimed')
                    if not status:
                        status.append('Safe')
                    
                    f.write(f"- {pkg.get('name', 'Unknown')} ({pkg.get('package_manager', 'Unknown')}) - {', '.join(status)}\n")

class WorkingBugBountyAnalyzer:
    """Working bug bounty analyzer that handles missing dependencies"""
    
    def __init__(self, github_token: Optional[str] = None, output_dir: str = "results", org_name: str = None):
        self.github_client = WorkingGitHubClient(github_token)
        self.repo_cloner = RepositoryCloner()
        self.package_extractor = WorkingPackageExtractor()
        self.npm_checker = WorkingNPMChecker()
        self.reporter = WorkingReporter(output_dir, org_name)
    
    def analyze_organization(self, org_name: str, include_private: bool = False, 
                           include_deleted: bool = True, max_repos: int = 10) -> Dict:
        """Analyze a GitHub organization"""
        print(f"Analyzing organization: {org_name}")
        
        # Step 1: Get repositories (minimal API calls)
        print("Fetching repository list...")
        repos = self.github_client.get_organization_repositories(org_name, include_private)
        
        if not repos:
            print("No repositories found")
            return {'repositories': [], 'packages': [], 'commits': [], 'statistics': {}}
        
        print(f"Found {len(repos)} repositories")
        
        # Step 2: Clone repositories locally (avoids API rate limits)
        print("Cloning repositories locally...")
        cloned_repos = self.repo_cloner.clone_repositories(repos, include_private, max_repos)
        
        if not cloned_repos:
            print("No repositories cloned successfully")
            return {'repositories': [], 'packages': [], 'commits': [], 'statistics': {}}
        
        print(f"Successfully cloned {len(cloned_repos)} repositories")
        
        # Step 3: Extract packages from local repositories
        print("Extracting packages from local repositories...")
        all_packages = []
        for i, repo in enumerate(cloned_repos, 1):
            print(f"  [{i}/{len(cloned_repos)}] {repo['name']}")
            packages = self.package_extractor.extract_packages_from_local_repo(
                repo['local_path'], repo['name']
            )
            all_packages.extend(packages)
        
        # Step 4: Check NPM packages
        print("Checking NPM packages...")
        npm_packages = [pkg for pkg in all_packages if pkg.get('package_manager') == 'npm']
        if npm_packages:
            checked_packages = self.npm_checker.check_packages(npm_packages)
            
            # Update packages with check results
            package_map = {pkg['name']: pkg for pkg in all_packages}
            for checked_pkg in checked_packages:
                if checked_pkg['name'] in package_map:
                    package_map[checked_pkg['name']].update(checked_pkg)
        
        # Step 5: Analyze commits (if requested) - using API but only for cloned repos
        all_commits = []
        if include_deleted:
            print("Analyzing commits...")
            for i, repo in enumerate(cloned_repos, 1):
                print(f"  [{i}/{len(cloned_repos)}] {repo['name']}")
                commits = self.github_client.get_repository_commits(repo['full_name'])
                all_commits.extend(commits)
        
        # Step 6: Generate statistics
        vulnerable_count = sum(1 for pkg in all_packages if pkg.get('is_vulnerable', False))
        unclaimed_count = sum(1 for pkg in all_packages if pkg.get('is_unclaimed', False))
        
        stats = {
            'total_repositories': len(cloned_repos),
            'total_packages': len(all_packages),
            'vulnerable_packages': vulnerable_count,
            'unclaimed_packages': unclaimed_count,
            'total_commits': len(all_commits),
            'clone_statistics': self.repo_cloner.get_clone_statistics(),
            'npm_checks': {
                'total_checked': len(npm_packages),
                'vulnerable': len(self.npm_checker.vulnerable_packages),
                'unclaimed': len(self.npm_checker.unclaimed_packages)
            }
        }
        
        # Step 7: Generate reports
        print("Generating reports...")
        analysis_data = {
            'repositories': cloned_repos,
            'packages': all_packages,
            'commits': all_commits,
            'statistics': stats,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        report_files = self.reporter.generate_reports(analysis_data)
        
        # Display summary
        print("\n" + "="*60)
        print("ANALYSIS SUMMARY")
        print("="*60)
        print(f"Repositories cloned: {stats['total_repositories']}")
        print(f"Total packages found: {stats['total_packages']}")
        print(f"Vulnerable packages: {stats['vulnerable_packages']}")
        print(f"Unclaimed packages: {stats['unclaimed_packages']}")
        print(f"Commits analyzed: {stats['total_commits']}")
        print(f"Clone success rate: {stats['clone_statistics']['success_rate']:.1f}%")
        print(f"Reports saved to: {self.reporter.output_dir}")
        print(f"Organization folder: {self.reporter.output_dir.name}")
        print(f"Cloned repos location: {self.repo_cloner.base_dir}")
        
        if vulnerable_count > 0 or unclaimed_count > 0:
            risk_level = "HIGH" if (vulnerable_count + unclaimed_count) > 10 else "MEDIUM"
            print(f"Risk Level: {risk_level}")
        
        return analysis_data

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bug Bounty Package Analyzer')
    parser.add_argument('--org', required=True, help='GitHub organization name')
    parser.add_argument('--token', help='GitHub personal access token')
    parser.add_argument('--output', default='./results', help='Output directory for results')
    parser.add_argument('--private', action='store_true', help='Include private repositories')
    parser.add_argument('--deleted', action='store_true', default=True, help='Analyze deleted commits')
    parser.add_argument('--max-repos', type=int, default=10, help='Maximum number of repositories to analyze')
    
    args = parser.parse_args()
    
    if args.token:
        print("Using GitHub token for higher rate limits")
    else:
        print("Running without GitHub token (limited rate limits)")
    
    try:
        analyzer = WorkingBugBountyAnalyzer(args.token, args.output, args.org)
        results = analyzer.analyze_organization(
            org_name=args.org,
            include_private=args.private,
            include_deleted=args.deleted,
            max_repos=args.max_repos
        )
        
        print("\nAnalysis completed successfully!")
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during analysis: {e}")
        logger.error(f"Analysis error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
