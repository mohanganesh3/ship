import os
import sys

def check_dependencies():
    missing = []
    try:
        import fitz
    except ImportError:
        missing.append("pymupdf")
    try:
        import pymupdf4llm
    except ImportError:
        missing.append("pymupdf4llm")
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append("beautifulsoup4")
    try:
        import ebooklib
    except ImportError:
        missing.append("EbookLib")
    
    if missing:
        print(f"Missing dependencies for Tier 1 extraction: {', '.join(missing)}")
        print("Please run: pip install " + " ".join(missing))
        return False
    return True

if __name__ == "__main__":
    if check_dependencies():
        print("Dependencies validated. Ready for Tier 1 Extraction.")
