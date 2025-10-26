"""
Package and dependency extraction from various package managers
"""
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import xml.etree.ElementTree as ET
# Import settings with fallback
try:
    from config.settings import PACKAGE_FILE_PATTERNS, PACKAGE_MANAGERS
except ImportError:
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

logger = logging.getLogger(__name__)

class PackageExtractor:
    """Extracts packages and dependencies from various package managers"""
    
    def __init__(self):
        """Initialize package extractor"""
        self.extracted_packages = []
        self.package_files_found = []
    
    def extract_packages_from_directory(self, directory: Path) -> List[Dict]:
        """
        Extract packages from all package files in a directory
        
        Args:
            directory: Directory to search for package files
            
        Returns:
            List of extracted package dictionaries
        """
        logger.info(f"Extracting packages from directory: {directory}")
        
        self.extracted_packages = []
        self.package_files_found = []
        
        try:
            # Find all package files
            package_files = self._find_package_files(directory)
            
            # Extract packages from each file
            for file_path in package_files:
                packages = self._extract_packages_from_file(file_path)
                if packages:
                    self.extracted_packages.extend(packages)
                    self.package_files_found.append({
                        'file_path': str(file_path),
                        'package_count': len(packages)
                    })
            
            logger.info(f"Extracted {len(self.extracted_packages)} packages from {len(package_files)} files")
            return self.extracted_packages
            
        except Exception as e:
            logger.error(f"Error extracting packages from directory {directory}: {e}")
            return []
    
    def _find_package_files(self, directory: Path) -> List[Path]:
        """
        Find all package files in a directory
        
        Args:
            directory: Directory to search
            
        Returns:
            List of package file paths
        """
        package_files = []
        
        try:
            for pattern in PACKAGE_FILE_PATTERNS:
                for file_path in directory.glob(pattern):
                    if file_path.is_file():
                        package_files.append(file_path)
        except Exception as e:
            logger.error(f"Error finding package files in {directory}: {e}")
        
        return package_files
    
    def _extract_packages_from_file(self, file_path: Path) -> List[Dict]:
        """
        Extract packages from a single file
        
        Args:
            file_path: Path to the package file
            
        Returns:
            List of package dictionaries
        """
        try:
            # Determine package manager type
            package_type = self._identify_package_type(file_path)
            if not package_type:
                return []
            
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if not content:
                return []
            
            # Extract packages based on type
            if package_type == 'npm':
                return self._extract_npm_packages(content, file_path)
            elif package_type == 'pip':
                return self._extract_pip_packages(content, file_path)
            elif package_type == 'maven':
                return self._extract_maven_packages(content, file_path)
            elif package_type == 'gradle':
                return self._extract_gradle_packages(content, file_path)
            elif package_type == 'composer':
                return self._extract_composer_packages(content, file_path)
            elif package_type == 'cargo':
                return self._extract_cargo_packages(content, file_path)
            elif package_type == 'go':
                return self._extract_go_packages(content, file_path)
            elif package_type == 'ruby':
                return self._extract_ruby_packages(content, file_path)
            elif package_type == 'nuget':
                return self._extract_nuget_packages(content, file_path)
            
        except Exception as e:
            logger.error(f"Error extracting packages from {file_path}: {e}")
        
        return []
    
    def _identify_package_type(self, file_path: Path) -> Optional[str]:
        """
        Identify package manager type from file path
        
        Args:
            file_path: Path to the package file
            
        Returns:
            Package manager type or None
        """
        filename = file_path.name.lower()
        
        if filename == 'package.json':
            return 'npm'
        elif filename == 'yarn.lock':
            return 'yarn'
        elif filename == 'requirements.txt':
            return 'pip'
        elif filename == 'setup.py':
            return 'pip'
        elif filename == 'pyproject.toml':
            return 'pip'
        elif filename == 'pom.xml':
            return 'maven'
        elif filename in ['build.gradle', 'build.gradle.kts']:
            return 'gradle'
        elif filename == 'composer.json':
            return 'composer'
        elif filename == 'cargo.toml':
            return 'cargo'
        elif filename in ['go.mod', 'go.sum']:
            return 'go'
        elif filename in ['gemfile', 'gemfile.lock']:
            return 'ruby'
        elif filename == 'packages.config':
            return 'nuget'
        elif filename.endswith(('.csproj', '.vbproj')):
            return 'nuget'
        
        return None
    
    def _extract_npm_packages(self, content: str, file_path: Path) -> List[Dict]:
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
                    'file_path': str(file_path),
                    'source': 'package.json'
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
                            'file_path': str(file_path),
                            'source': 'package.json'
                        })
            
            # Extract scripts that might reference packages
            if 'scripts' in data and isinstance(data['scripts'], dict):
                for script_name, script_content in data['scripts'].items():
                    # Look for package references in scripts
                    package_refs = self._extract_package_references_from_text(script_content)
                    for pkg_name in package_refs:
                        packages.append({
                            'name': pkg_name,
                            'version': 'unknown',
                            'type': 'script_reference',
                            'category': 'scripts',
                            'package_manager': 'npm',
                            'file_path': str(file_path),
                            'source': f'package.json:scripts:{script_name}'
                        })
                        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing package.json {file_path}: {e}")
        
        return packages
    
    def _extract_pip_packages(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from requirements.txt, setup.py, or pyproject.toml"""
        packages = []
        
        try:
            if file_path.name == 'requirements.txt':
                packages = self._extract_requirements_txt(content, file_path)
            elif file_path.name == 'setup.py':
                packages = self._extract_setup_py(content, file_path)
            elif file_path.name == 'pyproject.toml':
                packages = self._extract_pyproject_toml(content, file_path)
        except Exception as e:
            logger.error(f"Error extracting pip packages from {file_path}: {e}")
        
        return packages
    
    def _extract_requirements_txt(self, content: str, file_path: Path) -> List[Dict]:
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
                    'file_path': str(file_path),
                    'source': f'requirements.txt:line_{line_num}'
                })
        
        return packages
    
    def _extract_setup_py(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from setup.py"""
        packages = []
        
        try:
            # Extract install_requires
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
                        'file_path': str(file_path),
                        'source': 'setup.py:install_requires'
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
                    'file_path': str(file_path),
                    'source': 'setup.py:main'
                })
                
        except Exception as e:
            logger.error(f"Error parsing setup.py {file_path}: {e}")
        
        return packages
    
    def _extract_pyproject_toml(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from pyproject.toml"""
        packages = []
        
        try:
            # This is a simplified implementation
            # In a real implementation, you'd use a TOML parser
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
                            'file_path': str(file_path),
                            'source': f'pyproject.toml:line_{line_num}'
                        })
        except Exception as e:
            logger.error(f"Error parsing pyproject.toml {file_path}: {e}")
        
        return packages
    
    def _extract_maven_packages(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from pom.xml"""
        packages = []
        
        try:
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
                    'file_path': str(file_path),
                    'source': 'pom.xml:main'
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
                        'file_path': str(file_path),
                        'source': 'pom.xml:dependencies'
                    })
                    
        except ET.ParseError as e:
            logger.error(f"Error parsing pom.xml {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error extracting Maven packages from {file_path}: {e}")
        
        return packages
    
    def _extract_gradle_packages(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from build.gradle"""
        packages = []
        
        try:
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
                        'file_path': str(file_path),
                        'source': 'build.gradle'
                    })
        except Exception as e:
            logger.error(f"Error extracting Gradle packages from {file_path}: {e}")
        
        return packages
    
    def _extract_composer_packages(self, content: str, file_path: Path) -> List[Dict]:
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
                    'file_path': str(file_path),
                    'source': 'composer.json'
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
                            'file_path': str(file_path),
                            'source': 'composer.json'
                        })
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing composer.json {file_path}: {e}")
        
        return packages
    
    def _extract_cargo_packages(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from Cargo.toml"""
        packages = []
        
        try:
            # This is a simplified implementation
            # In a real implementation, you'd use a TOML parser
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
                        'file_path': str(file_path),
                        'source': f'Cargo.toml:line_{line_num}'
                    })
        except Exception as e:
            logger.error(f"Error extracting Cargo packages from {file_path}: {e}")
        
        return packages
    
    def _extract_go_packages(self, content: str, file_path: Path) -> List[Dict]:
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
                            'file_path': str(file_path),
                            'source': f'go.mod:line_{line_num}'
                        })
        except Exception as e:
            logger.error(f"Error extracting Go packages from {file_path}: {e}")
        
        return packages
    
    def _extract_ruby_packages(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from Gemfile"""
        packages = []
        
        try:
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
                            'file_path': str(file_path),
                            'source': f'Gemfile:line_{line_num}'
                        })
        except Exception as e:
            logger.error(f"Error extracting Ruby packages from {file_path}: {e}")
        
        return packages
    
    def _extract_nuget_packages(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from packages.config or .csproj"""
        packages = []
        
        try:
            if file_path.name == 'packages.config':
                packages = self._extract_packages_config(content, file_path)
            elif file_path.name.endswith(('.csproj', '.vbproj')):
                packages = self._extract_csproj_packages(content, file_path)
        except Exception as e:
            logger.error(f"Error extracting NuGet packages from {file_path}: {e}")
        
        return packages
    
    def _extract_packages_config(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from packages.config"""
        packages = []
        
        try:
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
                        'file_path': str(file_path),
                        'source': 'packages.config'
                    })
        except ET.ParseError as e:
            logger.error(f"Error parsing packages.config {file_path}: {e}")
        
        return packages
    
    def _extract_csproj_packages(self, content: str, file_path: Path) -> List[Dict]:
        """Extract packages from .csproj files"""
        packages = []
        
        try:
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
                        'file_path': str(file_path),
                        'source': '.csproj'
                    })
        except ET.ParseError as e:
            logger.error(f"Error parsing .csproj {file_path}: {e}")
        
        return packages
    
    def _parse_pip_specification(self, spec: str) -> Tuple[str, str]:
        """
        Parse pip package specification
        
        Args:
            spec: Package specification string
            
        Returns:
            Tuple of (name, version)
        """
        spec = spec.strip()
        
        # Handle various version specifiers
        for operator in ['==', '>=', '<=', '>', '<', '~=', '!=']:
            if operator in spec:
                name, version = spec.split(operator, 1)
                return name.strip(), f"{operator}{version.strip()}"
        
        # No version specifier
        return spec, 'unknown'
    
    def _extract_package_references_from_text(self, text: str) -> List[str]:
        """
        Extract package references from arbitrary text (e.g., scripts)
        
        Args:
            text: Text to search for package references
            
        Returns:
            List of potential package names
        """
        packages = []
        
        # Look for common package reference patterns
        patterns = [
            r'npm\s+install\s+([a-zA-Z0-9@\-_/]+)',
            r'yarn\s+add\s+([a-zA-Z0-9@\-_/]+)',
            r'pip\s+install\s+([a-zA-Z0-9\-_]+)',
            r'composer\s+require\s+([a-zA-Z0-9\-_/]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            packages.extend(matches)
        
        return packages
    
    def get_extraction_statistics(self) -> Dict:
        """
        Get statistics about package extraction
        
        Returns:
            Dictionary with extraction statistics
        """
        package_managers = {}
        package_types = {}
        total_packages = len(self.extracted_packages)
        
        for package in self.extracted_packages:
            pkg_manager = package.get('package_manager', 'unknown')
            pkg_type = package.get('type', 'unknown')
            
            package_managers[pkg_manager] = package_managers.get(pkg_manager, 0) + 1
            package_types[pkg_type] = package_types.get(pkg_type, 0) + 1
        
        return {
            'total_packages': total_packages,
            'package_files_found': len(self.package_files_found),
            'package_managers': package_managers,
            'package_types': package_types,
            'files_processed': len(self.package_files_found)
        }
