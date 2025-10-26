# Quick Usage Guide

## Basic Usage

```bash
# Analyze a public organization
python src/main.py --org microsoft

# Analyze with GitHub token for higher rate limits
python src/main.py --org microsoft --token your_github_token

# Analyze more repositories
python src/main.py --org microsoft --token your_github_token --max-repos 20
```

## Advanced Usage

```bash
# Include private repositories
python src/main.py --org your-org --token your_token --private

# Custom output directory
python src/main.py --org microsoft --output ./my-results

# Full analysis with all options
python src/main.py --org microsoft --token your_token --private --deleted --max-repos 50 --output ./results
```

## Output Files

The tool generates reports in multiple formats:

- `bug_bounty_analysis_TIMESTAMP.json` - Complete analysis data
- `bug_bounty_packages_TIMESTAMP.csv` - Package details for spreadsheet analysis  
- `bug_bounty_report_TIMESTAMP.html` - Interactive HTML report
- `bug_bounty_report_TIMESTAMP.txt` - Human-readable text summary

## Example Output

```
Analyzing organization: microsoft
Fetching repositories...
Analyzing 10 repositories...
Extracting packages...
Checking NPM packages...
Analyzing commits...
Generating reports...

============================================================
ANALYSIS SUMMARY
============================================================
Repositories analyzed: 10
Total packages found: 45
Vulnerable packages: 2
Unclaimed packages: 3
Commits analyzed: 1250
Reports saved to: results
Risk Level: MEDIUM
```
