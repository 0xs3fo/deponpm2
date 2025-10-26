#!/usr/bin/env python3
"""
Test script to verify the installation and basic functionality
"""
import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test basic imports
        import asyncio
        import logging
        import json
        import csv
        import xml.etree.ElementTree as ET
        print("[OK] Basic Python modules imported successfully")
        
        # Test third-party imports
        import click
        print("[OK] Click imported successfully")
        
        from rich.console import Console
        print("[OK] Rich imported successfully")
        
        import pandas as pd
        print("[OK] Pandas imported successfully")
        
        import requests
        print("[OK] Requests imported successfully")
        
        import aiohttp
        print("[OK] Aiohttp imported successfully")
        
        import git
        print("[OK] GitPython imported successfully")
        
        from github import Github
        print("[OK] PyGithub imported successfully")
        
        # Test our modules
        sys.path.append(str(Path(__file__).parent / "src"))
        
        from github_client import GitHubClient
        print("[OK] GitHubClient imported successfully")
        
        from repo_cloner import RepositoryCloner
        print("[OK] RepositoryCloner imported successfully")
        
        from commit_analyzer import CommitAnalyzer
        print("[OK] CommitAnalyzer imported successfully")
        
        from package_extractor import PackageExtractor
        print("[OK] PackageExtractor imported successfully")
        
        from npm_checker import NPMChecker
        print("[OK] NPMChecker imported successfully")
        
        from reporter import Reporter
        print("[OK] Reporter imported successfully")
        
        from main import BugBountyAnalyzer
        print("[OK] BugBountyAnalyzer imported successfully")
        
        print("\n[SUCCESS] All imports successful! The tool is ready to use.")
        return True
        
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print("Please install missing dependencies with: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without making API calls"""
    print("\nTesting basic functionality...")
    
    try:
        sys.path.append(str(Path(__file__).parent / "src"))
        from main import BugBountyAnalyzer
        
        # Test analyzer initialization
        analyzer = BugBountyAnalyzer()
        print("[OK] BugBountyAnalyzer initialized successfully")
        
        # Test package extractor
        from package_extractor import PackageExtractor
        extractor = PackageExtractor()
        print("[OK] PackageExtractor initialized successfully")
        
        # Test reporter
        from reporter import Reporter
        reporter = Reporter()
        print("[OK] Reporter initialized successfully")
        
        print("[SUCCESS] Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("Bug Bounty Package Analyzer - Installation Test")
    print("=" * 50)
    
    import_success = test_imports()
    if import_success:
        func_success = test_basic_functionality()
        
        if func_success:
            print("\n[SUCCESS] All tests passed! The tool is ready to use.")
            print("\nTo run the analyzer:")
            print("python src/main.py --org <organization_name> --token <your_github_token>")
        else:
            print("\n[ERROR] Some functionality tests failed.")
    else:
        print("\n[ERROR] Installation test failed. Please check the error messages above.")
