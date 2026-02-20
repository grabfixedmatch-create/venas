import os
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
from urllib.parse import quote_plus
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================
# WORDPRESS CONFIG
# ==============================

WP_POST_URL = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
WP_TAGS_URL = "https://grabfixedmatch.com/wp-json/wp/v2/tags"

USERNAME = os.environ.get("WP_USERNAME")
APP_PASSWORD = os.environ.get("WP_APP_PASSWORD")

# ✅ MULTIPLE CATEGORY IDS
CATEGORY_IDS = [3764, 3886]

# ==============================
# CREATE SESSION WITH RETRIES
# ==============================

def create_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    return session

session = create_session()

# ==============================
# FORMAT TODAY'S DATE
# ==============================

today = datetime.now()
formatted_date = today.strftime("%A – %d/%m/%Y")

# ==============================
# SCRAPE VENASBET
# ==============================

VENASBET_URL = "https://www.venasbet.com/"

response = session.get(VENASBET_URL)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
table = soup.find("table", class_="table table-striped text-center mastro-tips")

matches = []
tags_to_add = []

# Fixed SEO Tags
fixed_tags = [
    "venasbet prediction",
    "venasbet prediction for today and tomorrow"
]

tags_to_add.extend(fixed_tags)

if table:
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else []

    random.shuffle(rows)
    rows = rows[:4]  # Limit to 4 matches

    for row in rows:
        cols = [td.get_text(strip=True, separator=" ") for td in row.find_all("td")]

        if len(cols) == 4:
            team_text = cols[2]

            search_query = quote_plus(team_text + " result")
            result_link = f'<a href="https://www.google.com/search?q={search_query}" target="_blank">Check</a>'

            matches.append({
                "time": cols[0],
                "league": cols[1],
                "teams": team_text,
                "prediction": cols[3],
                "result": result_link,
            })

# ==============================
# GENERATE TAGS FROM TEAMS
# ==============================

for match in matches:
    teams = match["teams"].replace("VS", "|").split("|")

    for team in teams:
        team = team.strip()
        if team:
            if team not in tags_to_add:
                tags_to_add.append(team)

            fixed_tag = f"{team} Fixed Matches"
            if fixed_tag not in tags_to_add:
                tags_to_add.append(fixed_tag)

# ==============================
# LOAD RANDOM USEFUL LINKS
# ==============================

GITHUB_LINKS_URL = "https://raw.githubusercontent.com/grabfixedmatch-create/venas/main/football_links.txt"

response = session.get(GITHUB_LINKS_URL)
response.raise_for_status()

all_links = [line.strip() for line in response.text.splitlines() if line.strip()]
selected_links = random.sample(all_links, min(3, len(all_links)))

links_html = "<br>".join(
    f'<a href="{link}" target="_blank">{link}</a>' 
    for link in selected_links
)

# ==============================
# BUILD POST HTML
# ==============================

html = """
<table id="free-tip">
    <thead>
        <tr>
            <th>Time</th>
            <th>League</th>
            <th>Teams</th>
            <th>Tip</th>
            <th style="width: 10%;">Result</th>
        </tr>
    </thead>
    <tbody>
"""

for m in matches:
    html += f"""
        <tr>
            <td>{m['time']}</td>
            <td>{m['league']}</td>
            <td>{m['teams']}</td>
            <td>{m['prediction']}</td>
            <td>{m['result']}</td>
        </tr>
    """

html += f"""
    </tbody>
</table>

<br>
<h3 class="links-per-post">Useful Links:</h3>
{links_html}
"""

# ==============================
# ENSURE TAGS EXIST IN WP
# ==============================

tag_ids = []

for tag_name in tags_to_add:
    try:
        resp = session.get(
            WP_TAGS_URL,
            params={"search": tag_name},
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
        )
        resp.raise_for_status()
        data = resp.json()

        if data:
            tag_ids.append(data[0]["id"])
        else:
            # Create new tag
            resp = session.post(
                WP_TAGS_URL,
                auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
                json={"name": tag_name}
            )
            resp.raise_for_status()
            tag_ids.append(resp.json()["id"])

        time.sleep(random.uniform(1.2, 2.5))

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error processing tag '{tag_name}': {e}")
        continue

# ==============================
# CREATE WORDPRESS POST
# ==============================

post_data = {
    "title": f"⚽ Fixed matches predictions, {formatted_date}",
    "content": html,
    "status": "publish",
    "tags": tag_ids,
    "categories": CATEGORY_IDS  # ✅ MULTIPLE CATEGORY SUPPORT
}

response = session.post(
    WP_POST_URL,
    json=post_data,
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
)

if response.status_code == 201:
    print("✅ Post created successfully in multiple categories!")
else:
    print("❌ Failed to create post:", response.text)
