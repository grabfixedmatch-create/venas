import os
import time
import random
import signal
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
from urllib.parse import quote_plus
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================
# GLOBAL TIMEOUT (5 MIN MAX)
# ==============================

def timeout_handler(signum, frame):
    raise Exception("⏰ Script timeout reached")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)

# ==============================
# WORDPRESS CONFIG
# ==============================

WP_POST_URL = "https://grabfixedmatch.com/wp-json/wp/v2/posts"

USERNAME = os.environ.get("WP_USERNAME")
APP_PASSWORD = os.environ.get("WP_APP_PASSWORD")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

CATEGORY_IDS = [3764, 3886]

if not USERNAME or not APP_PASSWORD:
    raise ValueError("Missing WordPress credentials")

# ==============================
# SESSION
# ==============================

def create_session():
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1,
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
# INTRO (AI)
# ==============================

intro_text = (
    f"<p>Today's football predictions for "
    f"{formatted_date} include carefully selected "
    f"matches based on team form, recent performances, "
    f"and statistical analysis.</p>"
)

try:
    if GOOGLE_API_KEY:

        import google.genai as genai

        client = genai.Client(api_key=GOOGLE_API_KEY)

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=(
                f"Write a short unique introduction "
                f"(150-200 characters) for football "
                f"predictions for {formatted_date}"
            )
        )

        if hasattr(response, "text") and response.text:
            intro_text = f"<p>{response.text}</p>"

except Exception as e:
    print(f"⚠️ AI intro failed: {e}")

# ==============================
# SCRAPE BETREKA TIPS
# ==============================

BETREKA_URL = "https://www.betrekatips.com/"

response = session.get(BETREKA_URL, timeout=15)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

table = soup.find(
    "table",
    class_="matches-table table-striped table-hover"
)

matches = []

if table:

    tbody = table.find("tbody")

    # fallback if no tbody exists
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    random.shuffle(rows)

    # ONLY 4 RANDOM MATCHES
    rows = rows[:4]

    for row in rows:

        try:

            league = ""
            match_time = ""
            teams = ""
            prediction = ""

            # League
            league_el = row.find("th", class_="social-left")

            if league_el:
                league = league_el.get_text(strip=True)

            # Time
            ths = row.find_all("th")

            if len(ths) > 1:
                match_time = ths[1].get_text(strip=True)

            # TDs
            tds = row.find_all("td")

            if len(tds) >= 2:

                # Teams
                teams = tds[0].get_text(
                    separator=" ",
                    strip=True
                )

                teams = " ".join(teams.split())

                # Prediction
                prediction = tds[1].get_text(strip=True)

                # Google result link
                search_query = quote_plus(
                    teams + " result"
                )

                result_link = (
                    f'<a href="https://www.google.com/search?q={search_query}" '
                    f'target="_blank">Check</a>'
                )

                matches.append({
                    "time": match_time,
                    "league": league,
                    "teams": teams,
                    "prediction": prediction,
                    "result": result_link,
                })

        except Exception as e:
            print(f"⚠️ Error parsing row: {e}")

# ==============================
# ANALYSIS (AI)
# ==============================

analysis_html = "<br><h2>Match Previews & Analysis</h2>"

if GOOGLE_API_KEY and matches:

    try:

        import google.genai as genai

        client = genai.Client(api_key=GOOGLE_API_KEY)

        matches_text = "\n".join([
            f"{m['teams']} ({m['league']})"
            for m in matches
        ])

        prompt = f"""
Write short football match analysis for each of these matches.

Matches:
{matches_text}

Instructions:
- DO NOT give predictions
- DO NOT repeat betting tips
- Focus on form, team performance, trends, and statistics
- 70-150 words per match
- Make each analysis unique
- Include soccer-prediction related keywords and make them bold in <strong> tag
- Use HTML format:

<h4>Team vs Team</h4>
<p>analysis...</p>
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        if hasattr(response, "text") and response.text:

            raw_html = response.text

            soup = BeautifulSoup(raw_html, "html.parser")

            accordion_html = '<div class="accordion">'

            items = soup.find_all(["h4", "p"])

            for i in range(0, len(items), 2):

                title = items[i]

                content = (
                    items[i + 1]
                    if i + 1 < len(items)
                    else None
                )

                if title and content:

                    accordion_html += f"""
                    <div class="accordion-item">
                        <button class="accordion-header">
                            {title.text}
                        </button>
                        <div class="accordion-content">
                            {str(content)}
                        </div>
                    </div>
                    """

            accordion_html += "</div>"

            analysis_html += accordion_html

    except Exception as e:
        print(f"⚠️ Analysis failed: {e}")

# ==============================
# LINKS
# ==============================

GITHUB_LINKS_URL = (
    "https://raw.githubusercontent.com/"
    "grabfixedmatch-create/venas/main/football_links.txt"
)

response = session.get(
    GITHUB_LINKS_URL,
    timeout=15
)

response.raise_for_status()

all_links = [
    line.strip()
    for line in response.text.splitlines()
    if line.strip()
]

selected_links = random.sample(
    all_links,
    min(3, len(all_links))
)

links_html = "<br>".join(
    f'<a href="{link}" target="_blank">{link}</a>'
    for link in selected_links
)

# ==============================
# BUILD HTML
# ==============================

html = intro_text + """
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
<td class="">{m['result']}</td>
</tr>
"""

html += "</tbody></table>"

html += analysis_html

html += f"""
<br>
<h3 class="links-per-post">Useful Links:</h3>
{links_html}
"""

# ==============================
# CREATE POST
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
    auth=HTTPBasicAuth(
        USERNAME,
        APP_PASSWORD
    ),
    timeout=15
)

if response.status_code == 201:
    print("✅ Post created successfully!")
else:
    print("❌ Failed:", response.text)
