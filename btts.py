import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests
import os
import time
from random import uniform

# ---------------- CONFIG ----------------
today = datetime.now()
formatted_date = today.strftime("%d.%m.%Y")
wp_url = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD")
category_id = 387

url = "https://zakabet.com/both-team-scores-bts-gg"
scraper = cloudscraper.create_scraper()  # bypass Cloudflare
html = scraper.get(url).text

soup = BeautifulSoup(html, "html.parser")
sections = soup.find_all("section", class_="match-section")

matches = []
tags_to_add = []

# Filter threshold
threshold = 74

# --------------- SCRAPE MATCHES ---------------
def extract_matches(threshold):
    found = []
    for section in sections:
        section_matches = section.find_all("li", class_="match-item")
        for match in section_matches:
            teams = [t.get_text(strip=True) for t in match.select(".team-name")]
            if len(teams) == 2:
                match_name = f"{teams[0]} VS {teams[1]}"
                team1, team2 = teams
            else:
                match_name = "Unknown Match"
                team1 = team2 = "Unknown"

            tip_elem = match.find("p", class_="picks-value")
            tip_text = tip_elem.get_text(" ", strip=True).replace("Tip:", "").strip().upper() if tip_elem else "N/A"

            prob_elem = match.find("p", class_="scores-value")
            prob = float(prob_elem.get_text(strip=True)) if prob_elem else 0.0

            if prob > threshold:
                search_query = match_name.replace(" ", "+")
                result_link = f'<a href="https://www.google.com/search?q={search_query}+result+{formatted_date}" target="_blank">Check</a>'
                found.append({
                    "date": formatted_date,
                    "teams": match_name,
                    "tip": tip_text,
                    "result": result_link,
                    "team1": team1,
                    "team2": team2
                })
    return found

matches = extract_matches(threshold)
if not matches:
    matches = extract_matches(71)

# ---------------- BUILD HTML TABLE ----------------
html_table = """
<table id="free-tip">
    <thead>
        <tr>
            <th>Date</th>
            <th>Match</th>
            <th>Tip</th>
            <th>FT</th>
        </tr>
    </thead>
    <tbody>
"""
for m in matches:
    html_table += f"""
        <tr>
            <td>{m['date']}</td>
            <td>{m['teams']}</td>
            <td>{m['tip']}</td>
            <td>{m['result']}</td>
        </tr>
    """
html_table += """
    </tbody>
</table>
"""

# ---------------- RETRY HELPERS ----------------
def safe_request(method, url, retries=5, **kwargs):
    """Retry with exponential backoff for 429 errors."""
    for attempt in range(retries):
        resp = requests.request(method, url, **kwargs)
        if resp.status_code == 429:
            wait_time = min(30, 3 * (2 ** attempt))  # exponential backoff
            print(f"⚠️ 429 Too Many Requests → Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue
        resp.raise_for_status()
        return resp
    raise Exception(f"❌ Failed after {retries} retries: {url}")

# ---------------- CREATE OR FETCH TAGS ----------------
tag_ids = []
for m in matches:
    t1 = m["team1"]
    t2 = m["team2"]
    tags_to_add = [
        f"{t1} vs {t2} BTTS prediction",
        f"{t1} BTTS soccer predictions",
        f"{t2} BTTS soccer predictions"
    ]

    for tag_name in tags_to_add:
        try:
            # Random small delay to avoid hitting rate limit too fast
            time.sleep(uniform(1.5, 3.5))

            # Check if tag exists
            response = safe_request(
                "GET",
                f"https://grabfixedmatch.com/wp-json/wp/v2/tags?search={tag_name}",
                auth=HTTPBasicAuth(username, app_password)
            )
            data = response.json()

            if data:
                tag_ids.append(data[0]["id"])
            else:
                # Create new tag
                create_resp = safe_request(
                    "POST",
                    "https://grabfixedmatch.com/wp-json/wp/v2/tags",
                    auth=HTTPBasicAuth(username, app_password),
                    json={"name": tag_name}
                )
                tag_ids.append(create_resp.json()["id"])

        except Exception as e:
            print(f"⚠️ Skipped tag '{tag_name}' due to error: {e}")

# ---------------- POST TO WORDPRESS ----------------
post_title = f"⚽ BTTS Soccer Predictions - {formatted_date}"

post_data = {
    "title": post_title,
    "content": html_table,
    "status": "publish",
    "categories": [category_id],
    "tags": tag_ids
}

try:
    response = safe_request(
        "POST",
        wp_url,
        json=post_data,
        auth=HTTPBasicAuth(username, app_password)
    )

    if response.status_code == 201:
        print("✅ Post created successfully!")
    else:
        print(f"❌ Failed to create post: {response.text}")

except Exception as e:
    print(f"❌ Final post error: {e}")
