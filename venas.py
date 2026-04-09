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
# SCRAPE
# ==============================

VENASBET_URL = "https://www.venasbet.com/"
response = session.get(VENASBET_URL)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
table = soup.find("table", class_="table table-striped text-center mastro-tips")

matches = []

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

def call_ai_with_long_wait(prompt):
    MAX_TOTAL_WAIT = 900  # 15 minutes
    WAIT_BETWEEN = 60     # retry every 60s
    elapsed = 0

    while elapsed < MAX_TOTAL_WAIT:
        try:
            print(f"➡️ Calling AI... (elapsed {elapsed}s)")

            response = requests.post(
                AI_URL,
                headers={
                    "Authorization": f"Bearer {AI_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
                json={"message": prompt},
                timeout=180
            )

            print("➡️ STATUS:", response.status_code)
            print("➡️ RAW TEXT:", response.text[:300])

            # SAFE JSON PARSE
            try:
                data = response.json()
            except Exception:
                print("❌ Not JSON response")
                data = None

            if data and data.get("success") and data.get("response"):
                text = data["response"].strip()

                if len(text) > 50:
                    print("✅ AI SUCCESS")
                    return text

        except Exception as e:
            print("❌ AI Error:", e)

        print("⏳ Waiting before retry...")
        time.sleep(WAIT_BETWEEN)
        elapsed += WAIT_BETWEEN

    print("⚠️ AI FAILED AFTER 15 MINUTES")
    return None

# ==============================
# AI INTRO ONLY
# ==============================

intro_prompt = f"""
Write a 150-200 word introduction for today's football predictions ({formatted_date}).

Explain:
- why these matches are selected
- that analysis is based on form and stats
- encourage users to check predictions below

Write like a sports betting article.
"""

intro_text = call_ai_with_long_wait(intro_prompt)

# ==============================
# FALLBACK
# ==============================

if not intro_text:
    intro_text = f"""
Today's football predictions for {formatted_date} include carefully selected matches based on team form, recent performances, and statistical analysis.
These tips aim to highlight valuable opportunities across different competitions, helping users make more informed betting decisions.
Check the table below for today's top picks and insights.
"""

# CLEAN TEXT
intro_text = intro_text.replace("\n", " ").replace("**", "")

intro_html = f"<p>{intro_text}</p>"

# ==============================
# BUILD TABLE
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

table_html += "</tbody></table>"

# ==============================
# FINAL HTML
# ==============================

html = f"""
{intro_html}

<br>

{table_html}
"""

# ==============================
# POST TO WORDPRESS
# ==============================

post_data = {
    "title": f"⚽ Fixed matches predictions, {formatted_date}",
    "content": html,
    "status": "publish",
    "categories": CATEGORY_IDS
}

response = session.post(
    WP_POST_URL,
    json=post_data,
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
)

print("➡️ WP STATUS:", response.status_code)
print("➡️ WP RESPONSE:", response.text)
