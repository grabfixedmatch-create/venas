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

print("🌍 Fetching match data from:", url)
html = scraper.get(url).text

soup = BeautifulSoup(html, "html.parser")
sections = soup.find_all("section", class_="match-section")

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
            try:
                prob = float(prob_elem.get_text(strip=True))
            except (ValueError, AttributeError):
                prob = 0.0

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
    print("⚠️ No matches found above threshold, lowering threshold to 71")
    matches = extract_matches(71)

if not matches:
    print("❌ No matches found at all, aborting...")
    exit(0)

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


# ---------------- RETRY HELPER ----------------
def safe_request(method, url, retries=5, **kwargs):
    """Retry with exponential backoff for 429 and timeout errors."""
    for attempt in range(retries):
        try:
            resp = requests.request(method, url, timeout=20, **kwargs)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error: {e}. Waiting 5s before retry...")
            time.sleep(5)
            continue

        if resp.status_code == 429:
            wait_time = min(120, 5 * (2 ** attempt))
            print(f"⚠️ 429 Too Many Requests → Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
            continue

        try:
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error: {e}. Waiting 5s before retry...")
            time.sleep(5)

    # If we reach here, we failed all retries
    print(f"❌ Giving up on {url} after {retries} retries.")
    return None


# ---------------- COLLECT TAGS ----------------
tag_ids = []

try:
    print("🏷️ Collecting tags...")
    all_tag_names = []
    for m in matches:
        t1 = m["team1"]
        t2 = m["team2"]
        all_tag_names.extend([
            f"{t1} vs {t2} BTTS prediction",
            f"{t1} BTTS soccer predictions",
            f"{t2} BTTS soccer predictions"
        ])

    all_tag_names = list(dict.fromkeys(all_tag_names))
    existing_tags = {}

    # Fetch all existing tags (paginated)
    page = 1
    while True:
        resp = safe_request(
            "GET",
            "https://grabfixedmatch.com/wp-json/wp/v2/tags",
            params={"per_page": 100, "page": page},
            auth=HTTPBasicAuth(username, app_password)
        )
        if not resp:
            print("⚠️ Skipping tags due to API timeout.")
            existing_tags = {}
            tag_ids = []
            break

        tags = resp.json()
        if not tags:
            break
        for tag in tags:
            existing_tags[tag['name']] = tag['id']
        page += 1

    # Create missing tags
    for tag_name in all_tag_names:
        if tag_name in existing_tags:
            tag_ids.append(existing_tags[tag_name])
        else:
            time.sleep(uniform(1.5, 3.5))
            resp = safe_request(
                "POST",
                "https://grabfixedmatch.com/wp-json/wp/v2/tags",
                auth=HTTPBasicAuth(username, app_password),
                json={"name": tag_name}
            )
            if resp:
                tag_id = resp.json().get("id")
                if tag_id:
                    tag_ids.append(tag_id)
                    existing_tags[tag_name] = tag_id

except Exception as e:
    print(f"⚠️ Tag processing failed: {e}")
    tag_ids = []


# ---------------- POST TO WORDPRESS ----------------
post_title = f"⚽ BTTS Soccer Predictions - {formatted_date}"

post_data = {
    "title": post_title,
    "content": html_table,
    "status": "publish",
    "categories": [category_id],
}

# Only add tags if they exist
if tag_ids:
    post_data["tags"] = tag_ids
else:
    print("⚠️ No tags will be added to the post due to previous errors.")

print("📝 Creating WordPress post...")
response = safe_request(
    "POST",
    wp_url,
    json=post_data,
    auth=HTTPBasicAuth(username, app_password)
)

if response and response.status_code == 201:
    print("✅ Post created successfully!")
else:
    print(f"❌ Failed to create post: {response.text if response else 'No response received.'}")
