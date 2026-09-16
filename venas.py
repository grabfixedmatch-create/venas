import os
import random
import signal
import requests
import xmlrpc.client

from bs4 import BeautifulSoup
from datetime import datetime
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
# WORDPRESS CONFIG (XML-RPC)
# ==============================

WP_XMLRPC = "https://grabfixedmatch.com/xmlrpc.php"

USERNAME = os.environ.get("WP_USERNAME")
PASSWORD = os.environ.get("WP_APP_PASSWORD")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

CATEGORY_IDS = [3764, 3886]

if not USERNAME or not PASSWORD:
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
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    })

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
                f"(250-300 characters) for football "
                f"predictions for {formatted_date}"
            )
        )

        if hasattr(response, "text") and response.text:
            intro_text = f"<p>{response.text}</p>"

except Exception as e:
    print(f"⚠️ AI intro failed: {e}")

# ==============================
# SCRAPE BETENSURED TIPS
# ==============================

BETENSURED_URL = "https://www.betensured.com/"

response = session.get(BETENSURED_URL, timeout=20)

response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

# Find the expert picks table
table = soup.find("table", class_="expert-picks-table")

matches = []

if table:

    tbody = table.find("tbody")

    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    # Filter out locked rows (premium/members-only rows)
    available_rows = []

    for row in rows:

        # Skip rows that contain the lock icon (premium content)
        if row.find("i", class_="fa-lock"):
            continue

        # Must have a .set-1 span (team name) to be a valid match row
        if not row.find("span", class_="set-1"):
            continue

        available_rows.append(row)

    # Shuffle and pick 4 random available matches
    random.shuffle(available_rows)

    selected_rows = available_rows[:4]

    for row in selected_rows:

        try:

            league = ""
            teams = ""
            ft_result = ""
            expert_tip = ""
            stats_url = ""

            # League: <small> tag next to flag image
            small_el = row.find("small")

            if small_el:
                league = small_el.get_text(strip=True)

            # Teams: inside .set-1 span
            teams_el = row.find("span", class_="set-1")

            if teams_el:
                teams = teams_el.get_text(strip=True)

            # Stats link: first <a> inside the match name area
            link_el = row.find("a", href=True)

            if link_el:
                href = link_el.get("href", "")
                if href.startswith("http"):
                    stats_url = href
                else:
                    stats_url = "https://www.betensured.com" + href

            # All <td> elements in this row
            tds = row.find_all("td")

            # Expert Tip: look for <span style="color: red"><b>
            for td in tds:
                red_span = td.find("span", style=lambda s: s and "color: red" in s)
                if red_span:
                    b_tag = red_span.find("b")
                    if b_tag:
                        expert_tip = b_tag.get_text(strip=True)
                    break

            # FT (Outcome): second <td> containing a standalone <b>
            # It's the td right after the teams td (index 1 in visible tds)
            if len(tds) >= 2:
                b_tag = tds[1].find("b")
                if b_tag:
                    ft_result = b_tag.get_text(strip=True)

            # Google result link for this match
            search_query = quote_plus(teams + " result")

            result_link = (
                f'<a href="https://www.google.com/search?q={search_query}" '
                f'target="_blank">Check</a>'
            )

            # Stats link from betensured
            if stats_url:
                stats_link = (
                    f'<a href="{stats_url}" '
                    f'target="_blank">Stats</a>'
                )
            else:
                stats_link = ""

            if teams and expert_tip:

                matches.append({
                    "league": league,
                    "teams": teams,
                    "tip": expert_tip,
                    "ft": ft_result,
                    "result": result_link,
                    "stats": stats_link,
                })

        except Exception as e:
            print(f"⚠️ Error parsing row: {e}")

if not matches:
    print("⚠️ No matches scraped from betensured.com")

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
- 50-70 words per match
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

            soup = BeautifulSoup(
                raw_html,
                "html.parser"
            )

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
    timeout=20
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

links_html = "<br>".join([
    f'<a href="{link}" target="_blank">{link}</a>'
    for link in selected_links
])

# ==============================
# BUILD HTML
# ==============================

html = intro_text + """
<table id="free-tip">
<thead>
<tr>
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
<td>{m['league']}</td>
<td>{m['teams']}</td>
<td>{m['tip']}</td>
<td>{m['result']}</td>
</tr>
"""

html += "</tbody></table>"

html += analysis_html

html += f"""
<br>

<h3 class="links-per-post">
Useful Links:
</h3>

{links_html}
"""

# ==============================
# CREATE POST (XML-RPC)
# ==============================

try:

    client = xmlrpc.client.ServerProxy(WP_XMLRPC)

    post_data = {
        'title': f"Soccer predictions today, {formatted_date}",

        'description': html,

        'categories': [
            'Football Predictions'
        ]
    }

    post_id = client.metaWeblog.newPost(
        '',
        USERNAME,
        PASSWORD,
        post_data,
        True
    )

    print(
        f"✅ Post created successfully! "
        f"ID: {post_id}"
    )

except Exception as e:

    print(f"❌ Failed to create post: {e}")
