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
# AI CONFIG
# ==============================

AI_API_KEY = "apf_bin5bqsgsxxxbeo0fsnw9b72"
AI_URL = "https://apifreellm.com/api/v1/chat"

def call_ai(prompt):
    try:
        response = requests.post(
            AI_URL,
            headers={"Authorization": f"Bearer {AI_API_KEY}"},
            json={"message": prompt},
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print("AI Error:", e)
        return ""

# ==============================
# WORDPRESS CONFIG
# ==============================

WP_POST_URL = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
WP_TAGS_URL = "https://grabfixedmatch.com/wp-json/wp/v2/tags"

USERNAME = os.environ.get("WP_USERNAME")
APP_PASSWORD = os.environ.get("WP_APP_PASSWORD")

CATEGORY_IDS = [3764, 3886]

# ==============================
# SESSION
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
# DATE
# ==============================

today = datetime.now()
formatted_date = today.strftime("%A – %d/%m/%Y")

# ==============================
# SCRAPE
# ==============================

VENASBET_URL = "https://www.venasbet.com/"
response = session.get(VENASBET_URL)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
table = soup.find("table", class_="table table-striped text-center mastro-tips")

matches = []
tags_to_add = [
    "venasbet prediction",
    "venasbet prediction for today and tomorrow"
]

if table:
    rows = table.find("tbody").find_all("tr")
    random.shuffle(rows)
    rows = rows[:4]

    for row in rows:
        cols = [td.get_text(strip=True, separator=" ") for td in row.find_all("td")]

        if len(cols) == 4:
            team_text = cols[2]
            search_query = quote_plus(team_text + " result")

            matches.append({
                "time": cols[0],
                "league": cols[1],
                "teams": team_text,
                "prediction": cols[3],
                "result": f'<a href="https://www.google.com/search?q={search_query}" target="_blank">Check</a>',
            })

# ==============================
# AI: INTRO
# ==============================

intro_prompt = f"""
Write a 150-word SEO-friendly introduction for a football predictions article.

Date: {formatted_date}

Include:
- Mention today's football predictions
- Encourage users to check the table
- Use engaging tone
"""

intro_text = call_ai(intro_prompt)
time.sleep(25)

# ==============================
# AI: MATCH PREVIEWS
# ==============================

match_previews_html = ""

for match in matches:
    prompt = f"""
Write a detailed football match preview for:

{match['teams']}

Include:
- Recent form
- Head-to-head (if possible)
- Tactical analysis
- Prediction reasoning

Make it SEO-friendly with short paragraphs.
"""

    preview = call_ai(prompt)
    time.sleep(25)

    match_previews_html += f"""
    <h2>{match['teams']} Prediction & Preview</h2>
    <p>{preview}</p>
    """

# ==============================
# TAGS
# ==============================

for match in matches:
    teams = match["teams"].replace("VS", "|").split("|")
    for team in teams:
        team = team.strip()
        if team and team not in tags_to_add:
            tags_to_add.append(team)
            tags_to_add.append(f"{team} Fixed Matches")

# ==============================
# LINKS
# ==============================

GITHUB_LINKS_URL = "https://raw.githubusercontent.com/grabfixedmatch-create/venas/main/football_links.txt"

response = session.get(GITHUB_LINKS_URL)
all_links = [line.strip() for line in response.text.splitlines() if line.strip()]
selected_links = random.sample(all_links, min(3, len(all_links)))

links_html = "<br>".join(
    f'<a href="{link}" target="_blank">{link}</a>'
    for link in selected_links
)

# ==============================
# BUILD HTML
# ==============================

html = f"""
<p>{intro_text}</p>

<table id="free-tip">
<thead>
<tr>
<th>Time</th>
<th>League</th>
<th>Teams</th>
<th>Tip</th>
<th>Result</th>
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
{match_previews_html}

<br>
<h3 class="links-per-post">Useful Links:</h3>
{links_html}
"""

# ==============================
# TAG CREATION
# ==============================

tag_ids = []

for tag_name in tags_to_add:
    try:
        resp = session.get(
            WP_TAGS_URL,
            params={"search": tag_name},
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
        )
        data = resp.json()

        if data:
            tag_ids.append(data[0]["id"])
        else:
            resp = session.post(
                WP_TAGS_URL,
                auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
                json={"name": tag_name}
            )
            tag_ids.append(resp.json()["id"])

        time.sleep(1.5)

    except Exception as e:
        print("Tag error:", e)

# ==============================
# POST
# ==============================

post_data = {
    "title": f"⚽ Fixed matches predictions, {formatted_date}",
    "content": html,
    "status": "publish",
    "tags": tag_ids,
    "categories": CATEGORY_IDS
}

response = session.post(
    WP_POST_URL,
    json=post_data,
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
)

print("✅ DONE" if response.status_code == 201 else response.text)
