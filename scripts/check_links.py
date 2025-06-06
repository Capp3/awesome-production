#!/usr/bin/env python3

import json
import re
import sys
import time
from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException
import markdown
from pathlib import Path

# Configuration
TIMEOUT = 10  # seconds
USER_AGENT = 'Awesome-Production-Link-Checker/1.0'
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 2  # seconds

def extract_links_from_markdown(markdown_content):
    """Extract all links from markdown content with their sections."""
    links = []
    current_section = "Unknown"
    
    # Split content into lines
    lines = markdown_content.split('\n')
    
    for line in lines:
        # Check for section headers
        if line.startswith('### '):
            current_section = line[4:].strip()
        elif line.startswith('## '):
            current_section = line[3:].strip()
        elif line.startswith('# '):
            current_section = line[2:].strip()
            
        # Find links in the line
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.finditer(link_pattern, line)
        
        for match in matches:
            link_text, url = match.groups()
            links.append({
                'text': link_text,
                'url': url,
                'section': current_section
            })
    
    return links

def check_link(link):
    """Check a single link and return its status."""
    for attempt in range(MAX_RETRIES):
        try:
            headers = {'User-Agent': USER_AGENT}
            response = requests.get(
                link['url'],
                headers=headers,
                timeout=TIMEOUT,
                allow_redirects=True
            )
            
            original_domain = urlparse(link['url']).netloc
            final_domain = urlparse(response.url).netloc
            
            result = {
                'original_url': link['url'],
                'section': link['section'],
                'status': response.status_code,
                'final_url': response.url if response.url != link['url'] else None,
                'error': None
            }
            
            # Check for different domain redirects
            if original_domain != final_domain:
                result['error'] = f'Redirected to different domain: {final_domain}'
                return result
                
            # Check for error status codes
            if response.status_code >= 400:
                result['error'] = f'HTTP {response.status_code}'
                
            return result
            
        except RequestException as e:
            if attempt == MAX_RETRIES - 1:  # Last attempt
                return {
                    'original_url': link['url'],
                    'section': link['section'],
                    'status': None,
                    'final_url': None,
                    'error': str(e)
                }
            time.sleep(DELAY_BETWEEN_REQUESTS)  # Wait before retry

def main():
    # Read the markdown file
    readme_path = Path('readme.md')
    if not readme_path.exists():
        print("Error: readme.md not found")
        sys.exit(1)
        
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract links
    links = extract_links_from_markdown(content)
    total_links = len(links)
    
    print(f"Found {total_links} links to check")
    
    # Check each link
    problematic_links = []
    for i, link in enumerate(links, 1):
        print(f"Checking link {i}/{total_links}: {link['url']}")
        result = check_link(link)
        if result['error'] is not None:
            problematic_links.append(result)
            print(f"  Error: {result['error']}")
        else:
            print(f"  OK: {result['status']}")
        
        # Add delay between requests
        if i < total_links:  # Don't delay after the last link
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # Create report
    report = {
        'total_links': total_links,
        'problematic_links': problematic_links
    }
    
    # Write report to file
    with open('link_check_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    # Exit with error if there are problematic links
    if problematic_links:
        print(f"\nFound {len(problematic_links)} problematic links")
        sys.exit(1)
    else:
        print("\nAll links are valid")
        sys.exit(0)

if __name__ == '__main__':
    main()
