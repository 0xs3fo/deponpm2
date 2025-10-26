"""
NPM registry verification for package status and vulnerability checking
"""
import asyncio
import aiohttp
import logging
import time
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
# Import settings with fallback
try:
    from config.settings import NPM_REGISTRY_BASE, NPM_RATE_LIMIT, MAX_CONCURRENT_NPM_CHECKS, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, BACKOFF_FACTOR
except ImportError:
    NPM_REGISTRY_BASE = "https://registry.npmjs.org"
    NPM_RATE_LIMIT = 1000
    MAX_CONCURRENT_NPM_CHECKS = 10
    REQUEST_TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    BACKOFF_FACTOR = 2

logger = logging.getLogger(__name__)

class NPMChecker:
    """Checks package status and vulnerabilities in NPM registry"""
    
    def __init__(self):
        """Initialize NPM checker"""
        self.checked_packages = []
        self.failed_checks = []
        self.vulnerable_packages = []
        self.unclaimed_packages = []
        self.rate_limit_delay = 60 / NPM_RATE_LIMIT  # Delay between requests
    
    async def check_packages_async(self, packages: List[Dict]) -> List[Dict]:
        """
        Check packages asynchronously for status and vulnerabilities
        
        Args:
            packages: List of package dictionaries
            
        Returns:
            List of checked package dictionaries with status information
        """
        logger.info(f"Checking {len(packages)} packages in NPM registry")
        
        # Filter for NPM packages only
        npm_packages = [pkg for pkg in packages if pkg.get('package_manager') == 'npm']
        
        if not npm_packages:
            logger.info("No NPM packages found to check")
            return []
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_NPM_CHECKS)
        
        # Create tasks for checking packages
        tasks = []
        for package in npm_packages:
            task = self._check_single_package_async(package, semaphore)
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        checked_packages = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error checking package {npm_packages[i].get('name', 'unknown')}: {result}")
                self.failed_checks.append({
                    'package': npm_packages[i],
                    'error': str(result)
                })
            elif result:
                checked_packages.append(result)
        
        logger.info(f"Successfully checked {len(checked_packages)} packages")
        return checked_packages
    
    async def _check_single_package_async(self, package: Dict, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Check a single package asynchronously
        
        Args:
            package: Package dictionary
            semaphore: Semaphore to limit concurrent requests
            
        Returns:
            Updated package dictionary with status information
        """
        async with semaphore:
            try:
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
                package_name = package.get('name', '')
                if not package_name:
                    return None
                
                # Check package status
                package_info = await self._get_package_info(package_name)
                
                if package_info is None:
                    # Package not found - potentially unclaimed
                    updated_package = package.copy()
                    updated_package.update({
                        'npm_status': 'not_found',
                        'is_unclaimed': True,
                        'is_vulnerable': False,
                        'vulnerabilities': [],
                        'last_checked': time.time()
                    })
                    self.unclaimed_packages.append(updated_package)
                    return updated_package
                
                # Package exists - check for vulnerabilities
                vulnerabilities = await self._get_package_vulnerabilities(package_name)
                
                # Determine if package is vulnerable
                is_vulnerable = len(vulnerabilities) > 0
                
                updated_package = package.copy()
                updated_package.update({
                    'npm_status': 'found',
                    'is_unclaimed': False,
                    'is_vulnerable': is_vulnerable,
                    'vulnerabilities': vulnerabilities,
                    'package_info': package_info,
                    'last_checked': time.time()
                })
                
                if is_vulnerable:
                    self.vulnerable_packages.append(updated_package)
                
                return updated_package
                
            except Exception as e:
                logger.error(f"Error checking package {package.get('name', 'unknown')}: {e}")
                return None
    
    async def _get_package_info(self, package_name: str) -> Optional[Dict]:
        """
        Get package information from NPM registry
        
        Args:
            package_name: Name of the package
            
        Returns:
            Package information dictionary or None if not found
        """
        url = f"{NPM_REGISTRY_BASE}/{package_name}"
        
        for attempt in range(MAX_RETRIES):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {
                                'name': data.get('name', package_name),
                                'version': data.get('version', 'unknown'),
                                'description': data.get('description', ''),
                                'homepage': data.get('homepage', ''),
                                'repository': data.get('repository', {}),
                                'author': data.get('author', {}),
                                'license': data.get('license', ''),
                                'keywords': data.get('keywords', []),
                                'maintainers': data.get('maintainers', []),
                                'time': data.get('time', {}),
                                'versions': list(data.get('versions', {}).keys()) if 'versions' in data else []
                            }
                        elif response.status == 404:
                            return None
                        else:
                            logger.warning(f"Unexpected status code {response.status} for package {package_name}")
                            return None
                            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout checking package {package_name} (attempt {attempt + 1})")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))
                    continue
            except Exception as e:
                logger.warning(f"Error checking package {package_name} (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (BACKOFF_FACTOR ** attempt))
                    continue
        
        return None
    
    async def _get_package_vulnerabilities(self, package_name: str) -> List[Dict]:
        """
        Get package vulnerabilities from NPM audit API
        
        Args:
            package_name: Name of the package
            
        Returns:
            List of vulnerability dictionaries
        """
        # Note: NPM doesn't have a public vulnerability API
        # This is a placeholder for future implementation
        # In a real implementation, you might use:
        # - npm audit API (requires authentication)
        # - Snyk API
        # - GitHub Security Advisories
        # - CVE databases
        
        vulnerabilities = []
        
        try:
            # Placeholder implementation
            # In a real implementation, you would:
            # 1. Query vulnerability databases
            # 2. Check for known security issues
            # 3. Analyze package dependencies for vulnerabilities
            
            # For now, we'll do a simple check for common vulnerable package patterns
            if self._is_potentially_vulnerable_package(package_name):
                vulnerabilities.append({
                    'id': 'potential_vulnerability',
                    'severity': 'medium',
                    'title': 'Potentially vulnerable package',
                    'description': 'Package name suggests potential security risk',
                    'source': 'heuristic_check'
                })
                
        except Exception as e:
            logger.error(f"Error checking vulnerabilities for {package_name}: {e}")
        
        return vulnerabilities
    
    def _is_potentially_vulnerable_package(self, package_name: str) -> bool:
        """
        Check if a package name suggests potential vulnerability
        
        Args:
            package_name: Name of the package
            
        Returns:
            True if package might be vulnerable
        """
        # Common patterns that might indicate vulnerable packages
        suspicious_patterns = [
            'test', 'demo', 'example', 'sample', 'temp', 'tmp',
            'backup', 'old', 'legacy', 'deprecated', 'unused',
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
        
        # Check for names that are too similar to popular packages
        popular_packages = [
            'lodash', 'express', 'react', 'vue', 'angular', 'jquery',
            'axios', 'moment', 'bootstrap', 'webpack', 'babel'
        ]
        
        for popular in popular_packages:
            if self._is_similar_name(package_name, popular):
                return True
        
        return False
    
    def _is_similar_name(self, name1: str, name2: str) -> bool:
        """
        Check if two package names are similar (potential typosquatting)
        
        Args:
            name1: First package name
            name2: Second package name
            
        Returns:
            True if names are similar
        """
        # Simple similarity check based on character differences
        if abs(len(name1) - len(name2)) > 2:
            return False
        
        # Check for single character differences
        if len(name1) == len(name2):
            differences = sum(c1 != c2 for c1, c2 in zip(name1, name2))
            return differences <= 1
        
        # Check for single character insertion/deletion
        shorter, longer = (name1, name2) if len(name1) < len(name2) else (name2, name1)
        if len(longer) - len(shorter) == 1:
            # Check if shorter is a subsequence of longer
            i = j = 0
            while i < len(shorter) and j < len(longer):
                if shorter[i] == longer[j]:
                    i += 1
                j += 1
            return i == len(shorter)
        
        return False
    
    def check_packages_sync(self, packages: List[Dict]) -> List[Dict]:
        """
        Synchronous wrapper for checking packages
        
        Args:
            packages: List of package dictionaries
            
        Returns:
            List of checked package dictionaries
        """
        try:
            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.check_packages_async(packages))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in synchronous package checking: {e}")
            return []
    
    def get_check_statistics(self) -> Dict:
        """
        Get statistics about package checking
        
        Returns:
            Dictionary with checking statistics
        """
        total_checked = len(self.checked_packages)
        total_failed = len(self.failed_checks)
        total_vulnerable = len(self.vulnerable_packages)
        total_unclaimed = len(self.unclaimed_packages)
        
        return {
            'total_packages_checked': total_checked,
            'failed_checks': total_failed,
            'vulnerable_packages': total_vulnerable,
            'unclaimed_packages': total_unclaimed,
            'success_rate': (total_checked / (total_checked + total_failed) * 100) if (total_checked + total_failed) > 0 else 0,
            'vulnerability_rate': (total_vulnerable / total_checked * 100) if total_checked > 0 else 0,
            'unclaimed_rate': (total_unclaimed / total_checked * 100) if total_checked > 0 else 0
        }
    
    def get_vulnerable_packages(self) -> List[Dict]:
        """
        Get list of vulnerable packages
        
        Returns:
            List of vulnerable package dictionaries
        """
        return self.vulnerable_packages.copy()
    
    def get_unclaimed_packages(self) -> List[Dict]:
        """
        Get list of unclaimed packages
        
        Returns:
            List of unclaimed package dictionaries
        """
        return self.unclaimed_packages.copy()
    
    def get_failed_checks(self) -> List[Dict]:
        """
        Get list of failed package checks
        
        Returns:
            List of failed check dictionaries
        """
        return self.failed_checks.copy()
