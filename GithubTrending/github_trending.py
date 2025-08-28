
import requests
from bs4 import BeautifulSoup
import sys
import re


def fetch_trending_repos(language="python", time_range="daily", limit=5):
    """Fetch trending repositories from GitHub for specified language and time range, up to limit."""
    url = f"https://github.com/trending/{language.lower()}?since={time_range.lower()}"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    repos = []
    for repo in soup.find_all("article", class_="Box-row")[:limit]:  # Slice to limit number of repos
        h2_tag = repo.find("h2", class_="h3 lh-condensed")
        if h2_tag:
            anchor = h2_tag.find("a")
            if anchor:
                repo_url = f"https://github.com{anchor['href']}"
                repo_name = anchor.text.strip()
                description_tag = repo.find("p", class_="col-9 color-fg-muted my-1 pr-4")
                repo_description = description_tag.text.strip() if description_tag else "No description"
                # Extract stars
                stars_tag = repo.find("span", class_="d-inline-block float-sm-right")
                stars_today = None
                if stars_tag:
                    stars_text = stars_tag.get_text(strip=True)
                    match = re.search(r"([\d,]+) stars ", stars_text)
                    if match:
                        stars_today = match.group(1).replace(",", "")
                repos.append(
                    {
                        "url": repo_url,
                        "name": repo_name.replace("|","").replace(";",""),
                        "description": repo_description.replace("|","").replace(";",""),
                        "stars": stars_today if stars_today else "0",
                    }
                )
    return repos


def get_formatted_name(repo_name):
    """Prepare the name that is in gitlab provided as publisher / repository"""
    name_parts = repo_name.split("/")
    if len(name_parts) == 2:
        return f"**{name_parts[1].strip()}** by {name_parts[0].strip()}"
    return f"**{repo_name.strip()}**"


def prep_previous_content(previous_content):
    """Prepare the previous content for comparison using formatted name as unique identifier."""
    return previous_content.split(";")


def format_summary(new_repos, n=5):
    """Format a compact summary: **repo** by publisher|description|url|stars;... for first n repos"""
    if new_repos:
        entries = []
        for repo in new_repos[:n]:  # Slice to get only first n repos
            name_parts = repo["name"].split("/")
            if len(name_parts) == 2:
                formatted_name = f"**{name_parts[1].strip()}** by {name_parts[0].strip()}"
            else:
                formatted_name = f"**{repo['name'].strip()}**"
            entry = f"{formatted_name}|{repo['description']}|{repo['url']}|{repo['stars']}"
            entries.append(entry)
        return ";".join(entries)
    else:
        return ""


def main():
    previous_content = sys.argv[1] if len(sys.argv) >= 2 else ""
    language = sys.argv[2] if len(sys.argv) > 2 else "python"
    time_range = sys.argv[3] if len(sys.argv) > 3 else "daily"
    try:
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 5
        if limit < 1:
            limit = 5
    except ValueError:
        limit = 5

    # Validate time_range
    valid_time_ranges = ["daily", "weekly", "monthly"]
    if time_range.lower() not in valid_time_ranges:
        print(f"Error: time_range must be one of {valid_time_ranges}")
        return

    trending_repos = fetch_trending_repos(language, time_range, limit)

    previous_content_set = prep_previous_content(previous_content)

    # Filter out already scraped repositories using formatted name string
    new_repos = [repo for repo in trending_repos if get_formatted_name(repo["name"]) not in previous_content_set]

    # Print summary to terminal
    print(format_summary(new_repos, n=limit))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("")