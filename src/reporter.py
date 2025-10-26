"""
Comprehensive reporting system with multiple output formats
"""
import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import pandas as pd
# Import settings with fallback
try:
    from config.settings import RESULTS_DIR, SUPPORTED_OUTPUT_FORMATS
except ImportError:
    RESULTS_DIR = Path("results")
    SUPPORTED_OUTPUT_FORMATS = ['json', 'csv', 'html', 'txt']

logger = logging.getLogger(__name__)

class Reporter:
    """Generates comprehensive reports in multiple formats"""
    
    def __init__(self, output_dir: Path = RESULTS_DIR):
        """
        Initialize reporter
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def generate_reports(self, 
                        analysis_data: Dict[str, Any], 
                        output_formats: List[str] = None) -> Dict[str, Path]:
        """
        Generate reports in specified formats
        
        Args:
            analysis_data: Complete analysis data
            output_formats: List of output formats (default: all supported)
            
        Returns:
            Dictionary mapping format names to output file paths
        """
        if output_formats is None:
            output_formats = SUPPORTED_OUTPUT_FORMATS
        
        output_files = {}
        
        try:
            # Generate summary report
            summary_data = self._generate_summary_data(analysis_data)
            
            # Generate detailed reports
            for format_type in output_formats:
                if format_type == 'json':
                    output_files['json'] = self._generate_json_report(analysis_data)
                elif format_type == 'csv':
                    output_files['csv'] = self._generate_csv_report(analysis_data)
                elif format_type == 'html':
                    output_files['html'] = self._generate_html_report(analysis_data, summary_data)
                elif format_type == 'txt':
                    output_files['txt'] = self._generate_text_report(analysis_data, summary_data)
            
            logger.info(f"Generated reports in {len(output_files)} formats")
            return output_files
            
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
            return {}
    
    def _generate_summary_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from analysis data"""
        try:
            # Extract data from analysis
            repos_data = analysis_data.get('repositories', [])
            packages_data = analysis_data.get('packages', [])
            commits_data = analysis_data.get('commits', [])
            npm_checks = analysis_data.get('npm_checks', {})
            
            # Calculate statistics
            total_repos = len(repos_data)
            total_packages = len(packages_data)
            total_commits = len(commits_data)
            
            # Package statistics
            package_managers = {}
            package_types = {}
            vulnerable_packages = []
            unclaimed_packages = []
            
            for package in packages_data:
                pkg_manager = package.get('package_manager', 'unknown')
                pkg_type = package.get('type', 'unknown')
                
                package_managers[pkg_manager] = package_managers.get(pkg_manager, 0) + 1
                package_types[pkg_type] = package_types.get(pkg_type, 0) + 1
                
                if package.get('is_vulnerable', False):
                    vulnerable_packages.append(package)
                
                if package.get('is_unclaimed', False):
                    unclaimed_packages.append(package)
            
            # Repository statistics
            languages = {}
            private_repos = 0
            total_size = 0
            
            for repo in repos_data:
                if repo.get('private', False):
                    private_repos += 1
                
                if repo.get('size'):
                    total_size += repo['size']
                
                language = repo.get('language')
                if language:
                    languages[language] = languages.get(language, 0) + 1
            
            # NPM check statistics
            npm_stats = npm_checks.get('statistics', {})
            
            return {
                'timestamp': self.timestamp,
                'analysis_summary': {
                    'total_repositories': total_repos,
                    'total_packages': total_packages,
                    'total_commits_analyzed': total_commits,
                    'vulnerable_packages': len(vulnerable_packages),
                    'unclaimed_packages': len(unclaimed_packages),
                    'private_repositories': private_repos,
                    'total_size_mb': round(total_size / 1024, 2)
                },
                'package_managers': package_managers,
                'package_types': package_types,
                'languages': languages,
                'npm_check_statistics': npm_stats,
                'risk_assessment': self._assess_risk_level(vulnerable_packages, unclaimed_packages)
            }
            
        except Exception as e:
            logger.error(f"Error generating summary data: {e}")
            return {}
    
    def _assess_risk_level(self, vulnerable_packages: List[Dict], unclaimed_packages: List[Dict]) -> Dict[str, Any]:
        """Assess overall risk level based on findings"""
        total_risks = len(vulnerable_packages) + len(unclaimed_packages)
        
        if total_risks == 0:
            risk_level = "LOW"
            risk_score = 0
        elif total_risks < 5:
            risk_level = "MEDIUM"
            risk_score = 1
        elif total_risks < 20:
            risk_level = "HIGH"
            risk_score = 2
        else:
            risk_level = "CRITICAL"
            risk_score = 3
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'total_risks': total_risks,
            'vulnerable_count': len(vulnerable_packages),
            'unclaimed_count': len(unclaimed_packages)
        }
    
    def _generate_json_report(self, analysis_data: Dict[str, Any]) -> Path:
        """Generate JSON report"""
        output_file = self.output_dir / f"bug_bounty_analysis_{self.timestamp}.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"JSON report generated: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating JSON report: {e}")
            return None
    
    def _generate_csv_report(self, analysis_data: Dict[str, Any]) -> Path:
        """Generate CSV report with package details"""
        output_file = self.output_dir / f"bug_bounty_packages_{self.timestamp}.csv"
        
        try:
            packages_data = analysis_data.get('packages', [])
            
            if not packages_data:
                logger.warning("No package data found for CSV report")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(packages_data)
            
            # Select relevant columns
            columns = [
                'name', 'version', 'package_manager', 'type', 'category',
                'is_vulnerable', 'is_unclaimed', 'npm_status', 'file_path', 'source'
            ]
            
            # Filter to existing columns
            available_columns = [col for col in columns if col in df.columns]
            df_filtered = df[available_columns]
            
            # Save to CSV
            df_filtered.to_csv(output_file, index=False, encoding='utf-8')
            
            logger.info(f"CSV report generated: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating CSV report: {e}")
            return None
    
    def _generate_html_report(self, analysis_data: Dict[str, Any], summary_data: Dict[str, Any]) -> Path:
        """Generate HTML report"""
        output_file = self.output_dir / f"bug_bounty_report_{self.timestamp}.html"
        
        try:
            html_content = self._create_html_content(analysis_data, summary_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            return None
    
    def _create_html_content(self, analysis_data: Dict[str, Any], summary_data: Dict[str, Any]) -> str:
        """Create HTML content for the report"""
        vulnerable_packages = [pkg for pkg in analysis_data.get('packages', []) if pkg.get('is_vulnerable', False)]
        unclaimed_packages = [pkg for pkg in analysis_data.get('packages', []) if pkg.get('is_unclaimed', False)]
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bug Bounty Package Analysis Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .risk-high {{ color: #dc3545; }}
        .risk-medium {{ color: #ffc107; }}
        .risk-low {{ color: #28a745; }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }}
        .package-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .package-table th,
        .package-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .package-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .vulnerable {{
            background-color: #fff5f5;
        }}
        .unclaimed {{
            background-color: #fffbf0;
        }}
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .badge-vulnerable {{
            background-color: #dc3545;
            color: white;
        }}
        .badge-unclaimed {{
            background-color: #ffc107;
            color: black;
        }}
        .badge-safe {{
            background-color: #28a745;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Bug Bounty Package Analysis Report</h1>
            <p>Generated on {summary_data.get('timestamp', 'Unknown')}</p>
        </div>
        
        <div class="summary">
            <div class="stat-card">
                <div class="stat-number">{summary_data.get('analysis_summary', {}).get('total_repositories', 0)}</div>
                <div class="stat-label">Repositories</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{summary_data.get('analysis_summary', {}).get('total_packages', 0)}</div>
                <div class="stat-label">Packages Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-number risk-high">{summary_data.get('analysis_summary', {}).get('vulnerable_packages', 0)}</div>
                <div class="stat-label">Vulnerable Packages</div>
            </div>
            <div class="stat-card">
                <div class="stat-number risk-medium">{summary_data.get('analysis_summary', {}).get('unclaimed_packages', 0)}</div>
                <div class="stat-label">Unclaimed Packages</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Risk Assessment</h2>
            <p><strong>Risk Level:</strong> 
                <span class="risk-{summary_data.get('risk_assessment', {}).get('risk_level', 'UNKNOWN').lower()}">
                    {summary_data.get('risk_assessment', {}).get('risk_level', 'UNKNOWN')}
                </span>
            </p>
            <p><strong>Total Risks:</strong> {summary_data.get('risk_assessment', {}).get('total_risks', 0)}</p>
        </div>
        
        <div class="section">
            <h2>Vulnerable Packages ({len(vulnerable_packages)})</h2>
            {self._create_package_table(vulnerable_packages, 'vulnerable')}
        </div>
        
        <div class="section">
            <h2>Unclaimed Packages ({len(unclaimed_packages)})</h2>
            {self._create_package_table(unclaimed_packages, 'unclaimed')}
        </div>
        
        <div class="section">
            <h2>Package Manager Distribution</h2>
            {self._create_distribution_chart(summary_data.get('package_managers', {}))}
        </div>
        
        <div class="section">
            <h2>Language Distribution</h2>
            {self._create_distribution_chart(summary_data.get('languages', {}))}
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _create_package_table(self, packages: List[Dict], table_class: str) -> str:
        """Create HTML table for packages"""
        if not packages:
            return "<p>No packages found.</p>"
        
        html = f'<table class="package-table {table_class}">'
        html += '<tr><th>Name</th><th>Version</th><th>Manager</th><th>Type</th><th>Status</th><th>File</th></tr>'
        
        for package in packages:
            status_badge = self._get_status_badge(package)
            html += f'''
            <tr>
                <td>{package.get('name', 'Unknown')}</td>
                <td>{package.get('version', 'Unknown')}</td>
                <td>{package.get('package_manager', 'Unknown')}</td>
                <td>{package.get('type', 'Unknown')}</td>
                <td>{status_badge}</td>
                <td>{package.get('file_path', 'Unknown')}</td>
            </tr>
            '''
        
        html += '</table>'
        return html
    
    def _get_status_badge(self, package: Dict) -> str:
        """Get status badge HTML for a package"""
        if package.get('is_vulnerable', False):
            return '<span class="badge badge-vulnerable">Vulnerable</span>'
        elif package.get('is_unclaimed', False):
            return '<span class="badge badge-unclaimed">Unclaimed</span>'
        else:
            return '<span class="badge badge-safe">Safe</span>'
    
    def _create_distribution_chart(self, data: Dict[str, int]) -> str:
        """Create simple HTML distribution chart"""
        if not data:
            return "<p>No data available.</p>"
        
        total = sum(data.values())
        html = '<div style="margin-top: 15px;">'
        
        for key, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
            percentage = (value / total) * 100
            html += f'''
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>{key}</span>
                    <span>{value} ({percentage:.1f}%)</span>
                </div>
                <div style="background-color: #e9ecef; height: 20px; border-radius: 10px;">
                    <div style="background-color: #007bff; height: 100%; width: {percentage}%; border-radius: 10px;"></div>
                </div>
            </div>
            '''
        
        html += '</div>'
        return html
    
    def _generate_text_report(self, analysis_data: Dict[str, Any], summary_data: Dict[str, Any]) -> Path:
        """Generate text report"""
        output_file = self.output_dir / f"bug_bounty_report_{self.timestamp}.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("BUG BOUNTY PACKAGE ANALYSIS REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Generated: {summary_data.get('timestamp', 'Unknown')}\n\n")
                
                # Summary section
                f.write("SUMMARY\n")
                f.write("-" * 40 + "\n")
                summary = summary_data.get('analysis_summary', {})
                f.write(f"Total Repositories: {summary.get('total_repositories', 0)}\n")
                f.write(f"Total Packages: {summary.get('total_packages', 0)}\n")
                f.write(f"Vulnerable Packages: {summary.get('vulnerable_packages', 0)}\n")
                f.write(f"Unclaimed Packages: {summary.get('unclaimed_packages', 0)}\n")
                f.write(f"Private Repositories: {summary.get('private_repositories', 0)}\n")
                f.write(f"Total Size: {summary.get('total_size_mb', 0)} MB\n\n")
                
                # Risk assessment
                f.write("RISK ASSESSMENT\n")
                f.write("-" * 40 + "\n")
                risk = summary_data.get('risk_assessment', {})
                f.write(f"Risk Level: {risk.get('risk_level', 'UNKNOWN')}\n")
                f.write(f"Total Risks: {risk.get('total_risks', 0)}\n\n")
                
                # Vulnerable packages
                f.write("VULNERABLE PACKAGES\n")
                f.write("-" * 40 + "\n")
                vulnerable_packages = [pkg for pkg in analysis_data.get('packages', []) if pkg.get('is_vulnerable', False)]
                if vulnerable_packages:
                    for pkg in vulnerable_packages:
                        f.write(f"- {pkg.get('name', 'Unknown')} ({pkg.get('version', 'Unknown')}) - {pkg.get('package_manager', 'Unknown')}\n")
                else:
                    f.write("No vulnerable packages found.\n")
                f.write("\n")
                
                # Unclaimed packages
                f.write("UNCLAIMED PACKAGES\n")
                f.write("-" * 40 + "\n")
                unclaimed_packages = [pkg for pkg in analysis_data.get('packages', []) if pkg.get('is_unclaimed', False)]
                if unclaimed_packages:
                    for pkg in unclaimed_packages:
                        f.write(f"- {pkg.get('name', 'Unknown')} ({pkg.get('version', 'Unknown')}) - {pkg.get('package_manager', 'Unknown')}\n")
                else:
                    f.write("No unclaimed packages found.\n")
                f.write("\n")
                
                # Package manager distribution
                f.write("PACKAGE MANAGER DISTRIBUTION\n")
                f.write("-" * 40 + "\n")
                for manager, count in summary_data.get('package_managers', {}).items():
                    f.write(f"{manager}: {count}\n")
                f.write("\n")
                
                # Language distribution
                f.write("LANGUAGE DISTRIBUTION\n")
                f.write("-" * 40 + "\n")
                for language, count in summary_data.get('languages', {}).items():
                    f.write(f"{language}: {count}\n")
                f.write("\n")
                
                f.write("=" * 80 + "\n")
                f.write("END OF REPORT\n")
                f.write("=" * 80 + "\n")
            
            logger.info(f"Text report generated: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error generating text report: {e}")
            return None
