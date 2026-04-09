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
# SCRAPE VENASBET
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
# AI CONFIG
# ==============================

AI_API_KEY = "apf_bin5bqsgsxxxbeo0fsnw9b72"
AI_URL = "https://apifreellm.com/api/v1/chat"

def call_ai(prompt):
    try:
        response = requests.post(
            AI_URL,
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={"message": prompt},
            timeout=120
        )

        data = response.json()
        print("AI RAW:", data)

        if data.get("success") and data.get("response"):
            return data["response"].strip()

    except Exception as e:
        print("AI Error:", e)

    return ""

# ==============================
# AI PROMPT
# ==============================

match_list_text = "\n".join([m['teams'] for m in matches])

ai_prompt = f"""
Write a football predictions article for today ({formatted_date}).

Matches:
{match_list_text}

Include:
- short introduction (100-150 words)
- for each match write a detailed preview (form, H2H, prediction)
- return in HTML or markdown
"""

# Wait before calling to avoid empty response
print("⏳ Waiting 45 seconds before calling AI...")
time.sleep(45)

ai_content_raw = call_ai(ai_prompt)

# ==============================
# MARKDOWN TO HTML
# ==============================

def markdown_to_html(text):
    text = text.replace("**", "")  # remove bold
    text = text.replace("\n\n", "</p><p>")
    text = text.replace("\n", "<br>")
    return f"<p>{text}</p>"

if ai_content_raw:
    ai_content = markdown_to_html(ai_content_raw)
else:
    # fallback if AI fails
    intro_fallback = f"""
    <p>Today's football predictions for {formatted_date} include exciting matches across multiple competitions.</p>
    """
    previews_fallback = ""
    for m in matches:
        previews_fallback += f"""
        <h2>{m['teams']} Prediction & Preview</h2>
        <p>{m['teams']} is expected to be a competitive match. Based on recent form and squad quality, this game could offer good scoring chances.</p>
        """
    ai_content = intro_fallback + previews_fallback

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
response.raise_for_status()

all_links = [line.strip() for line in response.text.splitlines() if line.strip()]
selected_links = random.sample(all_links, min(3, len(all_links)))

links_html = "<br>".join(
    f'<a href="{link}" target="_blank">{link}</a>'
    for link in selected_links
)

# ==============================
# TABLE HTML
# ==============================

table_html = """
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
    table_html += f"""
    <tr>
    <td>{m['time']}</td>
    <td>{m['league']}</td>
    <td>{m['teams']}</td>
    <td>{m['prediction']}</td>
    <td class="">{m['result']}</td>
    </tr>
    """

table_html += """
</tbody>
</table>
"""

# ==============================
# FINAL HTML
# ==============================

html = f"""
{ai_content}

<br>

{table_html}

<br>
<h3 class="links-per-post">Useful Links:</h3>
{links_html}
"""

# ==============================
# CREATE/GET TAGS IN WP
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
            resp = session.post(
                WP_TAGS_URL,
                auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
                json={"name": tag_name}
            )
            resp.raise_for_status()
            tag_ids.append(resp.json()["id"])

        time.sleep(random.uniform(1.2, 2.0))

    except Exception as e:
        print(f"Tag error: {e}")

# ==============================
# POST TO WORDPRESS
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

if response.status_code == 201:
    print("✅ Post created successfully!")
else:
    print("❌ Failed:", response.text)
