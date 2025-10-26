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
python main.py --org microsoft --token your_token --private --deleted --max-repos 50 --output ./results
```

## How It Works

The tool now uses a **clone-first approach** to avoid GitHub API rate limits:

1. **Fetch Repository List** - Gets list of repositories (minimal API calls)
2. **Clone Locally** - Clones all repositories to `cloned_repos/` folder
3. **Extract Packages** - Analyzes local files for packages (no API calls)
4. **Check NPM** - Verifies packages against npm registry
5. **Analyze Commits** - Uses API only for commit analysis (optional)
6. **Generate Reports** - Creates reports in organization-specific folders

**Benefits:**
- ✅ **No Rate Limits** - Minimal API usage after initial fetch
- ✅ **Faster Analysis** - Local file processing is much faster
- ✅ **Offline Capable** - Can re-analyze without re-downloading
- ✅ **Complete Coverage** - Analyzes all files, not just API-accessible ones

## Output Files

The tool creates organization-specific folders and generates reports in multiple formats:

**Folder Structure:**
```
results/
├── GFG/                    # Organization-specific folder
│   ├── bug_bounty_analysis_TIMESTAMP.json
│   ├── bug_bounty_packages_TIMESTAMP.csv
│   ├── bug_bounty_report_TIMESTAMP.html
│   └── bug_bounty_report_TIMESTAMP.txt
├── microsoft/              # Another organization
│   └── [reports...]
└── google/                 # Yet another organization
    └── [reports...]
```

**Report Files (in each org folder):**
- `bug_bounty_analysis_TIMESTAMP.json` - Complete analysis data
- `bug_bounty_packages_TIMESTAMP.csv` - Package details for spreadsheet analysis  
- `bug_bounty_report_TIMESTAMP.html` - Interactive HTML report
- `bug_bounty_report_TIMESTAMP.txt` - Human-readable text summary

## Example Output

```
Analyzing organization: microsoft
Fetching repository list...
Found 150 repositories
Cloning repositories locally...
  [1/10] Cloning microsoft/vscode...
  [2/10] Cloning microsoft/TypeScript...
  [3/10] Cloning microsoft/playwright...
Successfully cloned 10 repositories
Extracting packages from local repositories...
  [1/10] microsoft/vscode
  [2/10] microsoft/TypeScript
  [3/10] microsoft/playwright
Checking NPM packages...
Analyzing commits...
Generating reports...

============================================================
ANALYSIS SUMMARY
============================================================
Repositories cloned: 10
Total packages found: 45
Vulnerable packages: 2
Unclaimed packages: 3
Commits analyzed: 1250
Clone success rate: 100.0%
Reports saved to: results/microsoft
Organization folder: microsoft
Cloned repos location: cloned_repos
Risk Level: MEDIUM
```
