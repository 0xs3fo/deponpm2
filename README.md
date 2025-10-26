# Bug Bounty Tool: GitHub Organization Package Analyzer

A comprehensive bug bounty hunting tool that analyzes GitHub organizations for potentially vulnerable or unclaimed packages. This tool helps security researchers and bug bounty hunters identify security risks in package dependencies and discover unclaimed package names that could be used for typosquatting attacks.

## 🚀 Features

- **Repository Analysis**: Clone and analyze all repositories in a GitHub organization
- **Package Discovery**: Extract packages from multiple package managers (npm, pip, maven, gradle, composer, cargo, go, ruby, nuget)
- **Commit History Analysis**: Analyze commit history including deleted commits to find historical package references
- **NPM Registry Verification**: Check package status against npm registry to identify unclaimed packages
- **Vulnerability Assessment**: Identify potentially vulnerable packages using heuristic analysis
- **Comprehensive Reporting**: Generate reports in multiple formats (JSON, CSV, HTML, TXT)
- **Parallel Processing**: Efficient processing of large organizations with many repositories
- **Rate Limiting**: Built-in rate limiting for GitHub API and npm registry requests

## 📋 Requirements

- Python 3.8+
- Git
- GitHub personal access token (recommended for higher rate limits)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd bug-bounty-package-analyzer
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up GitHub token (optional but recommended)**:
   ```bash
   export GITHUB_TOKEN="your_github_token_here"
   ```

## 🚀 Usage

### Basic Usage

```bash
python src/main.py --org organization-name
```

### Advanced Usage

```bash
python src/main.py --org organization-name \
    --token your_github_token \
    --output ./results \
    --private \
    --deleted \
    --max-repos 50 \
    --format json csv html
```

### Command Line Options

- `--org`: GitHub organization name (required)
- `--token`: GitHub personal access token (optional)
- `--output`: Output directory for results (default: ./results)
- `--private`: Include private repositories (default: false)
- `--deleted`: Analyze deleted commits (default: true)
- `--max-repos`: Maximum number of repositories to analyze (default: all)
- `--format`: Output formats for reports (default: json,csv,html,txt)

## 📁 Project Structure

```
bug-bounty-package-analyzer/
├── src/
│   ├── main.py              # Entry point
│   ├── github_client.py     # GitHub API interactions
│   ├── repo_cloner.py       # Repository cloning functionality
│   ├── commit_analyzer.py   # Commit history analysis
│   ├── package_extractor.py # Package/dependency extraction
│   ├── npm_checker.py       # NPM registry verification
│   └── reporter.py          # Results reporting
├── config/
│   └── settings.py          # Configuration settings
├── data/                    # Storage for cloned repos and results
├── logs/                    # Log files
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 Configuration

The tool can be configured by modifying `config/settings.py`:

- **Rate Limits**: Adjust API rate limits for GitHub and npm
- **Concurrency**: Set maximum concurrent operations
- **Timeouts**: Configure request and operation timeouts
- **Package Managers**: Add support for additional package managers
- **File Patterns**: Customize package file detection patterns

## 📊 Output Formats

### JSON Report
Complete analysis data in JSON format for programmatic processing.

### CSV Report
Package details in CSV format for spreadsheet analysis.

### HTML Report
Interactive HTML report with visualizations and risk assessment.

### Text Report
Human-readable text summary of findings.

## 🔍 Analysis Process

1. **Repository Discovery**: Fetch all repositories from the GitHub organization
2. **Repository Cloning**: Clone repositories to local storage for analysis
3. **Package Extraction**: Scan for package files and extract dependency information
4. **Commit Analysis**: Analyze commit history for deleted package references
5. **NPM Verification**: Check package status against npm registry
6. **Vulnerability Assessment**: Identify potentially vulnerable packages
7. **Report Generation**: Create comprehensive reports in multiple formats

## 🛡️ Security Features

### Vulnerability Detection
- Heuristic analysis of package names for potential security risks
- Detection of suspicious package patterns
- Identification of typosquatting opportunities

### Unclaimed Package Detection
- Verification against npm registry
- Identification of unclaimed package names
- Historical analysis of deleted packages

### Risk Assessment
- Automated risk scoring based on findings
- Categorization of risks by severity
- Recommendations for further investigation

## 📈 Performance

- **Parallel Processing**: Utilizes multiple threads for efficient processing
- **Rate Limiting**: Respects API rate limits to avoid throttling
- **Caching**: Implements caching to reduce redundant API calls
- **Progress Tracking**: Real-time progress indicators for long-running operations

## 🚨 Important Notes

### Legal and Ethical Considerations
- Only use this tool on organizations you have permission to analyze
- Respect GitHub's Terms of Service and API rate limits
- Ensure compliance with applicable laws and regulations
- Use responsibly for legitimate security research purposes

### Rate Limiting
- GitHub API: 5,000 requests/hour (authenticated), 60 requests/hour (unauthenticated)
- NPM Registry: 1,000 requests/hour (conservative limit)
- The tool automatically handles rate limiting and retries

### Resource Usage
- Large organizations may require significant disk space for cloned repositories
- Processing time scales with the number of repositories and commits
- Consider using `--max-repos` for initial testing

## 🔧 Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**:
   - Use a GitHub personal access token
   - Reduce concurrency in settings
   - Wait for rate limit reset

2. **Repository Clone Failures**:
   - Check network connectivity
   - Verify repository access permissions
   - Increase clone timeout in settings

3. **Memory Issues**:
   - Reduce `MAX_CONCURRENT_REPOS` in settings
   - Process repositories in smaller batches
   - Increase system memory

### Debug Mode
Enable debug logging by setting the environment variable:
```bash
export LOG_LEVEL=DEBUG
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for:

- Additional package manager support
- New vulnerability detection methods
- Performance improvements
- Bug fixes
- Documentation improvements

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and authorized security research purposes only. Users are responsible for ensuring they have proper authorization before analyzing any organization's repositories. The authors are not responsible for any misuse of this tool.

## 🆘 Support

For support, questions, or bug reports, please:

1. Check the troubleshooting section above
2. Review existing issues on GitHub
3. Create a new issue with detailed information
4. Include logs and error messages when reporting bugs

## 🔄 Updates

Stay updated with the latest features and security improvements by:

- Watching the repository for releases
- Following the changelog
- Updating dependencies regularly
- Reviewing security advisories

---

**Happy Bug Hunting! 🐛🔍**
