import os
import re
import time
import random
import signal
import requests
import xmlrpc.client

import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================
# GLOBAL TIMEOUT (8 MIN MAX)
# ==============================

def timeout_handler(signum, frame):
    raise Exception("⏰ Script timeout reached")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(480)

# ==============================
# CONFIG
# ==============================

WP_XMLRPC = "https://grabfixedmatch.com/xmlrpc.php"

USERNAME = os.environ.get("WP_USERNAME")
PASSWORD = os.environ.get("WP_APP_PASSWORD")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Optional: e.g. http://user:pass@host:port (set as a GitHub secret)
PROXY_URL = os.environ.get("PROXY_URL")

CATEGORY_IDS = [3764, 3886]

if not USERNAME or not PASSWORD:
    raise ValueError("Missing WordPress credentials")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

RETRY_STATUS = [429, 500, 502, 503, 504, 520, 521, 522, 523, 524]

# ==============================
# SESSIONS
# ==============================

def create_session():
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=RETRY_STATUS,
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    if PROXY_URL:
        session.proxies.update({"http": PROXY_URL, "https": PROXY_URL})

    return session


session = create_session()

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)
if PROXY_URL:
    scraper.proxies.update({"http": PROXY_URL, "https": PROXY_URL})


def fetch_html(url, must_contain=None, attempts=5, delay=8):
    """Fetch a page with cloudscraper, then plain session, with backoff."""
    clients = [("cloudscraper", scraper), ("requests", session)]

    for i in range(attempts):
        name, client = clients[i % len(clients)]
        try:
            resp = client.get(url, timeout=30, headers={
                "User-Agent": BROWSER_UA,
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            })

            if resp.status_code == 200 and (
                must_contain is None or must_contain in resp.text
            ):
                return resp.text

            print(f"⚠️ Attempt {i+1} ({name}) failed: status {resp.status_code}")

        except Exception as e:
            print(f"⚠️ Attempt {i+1} ({name}) error: {e}")

        sleep_time = delay * (i + 1) + random.uniform(1, 3)
        print(f"⏳ Retrying in {round(sleep_time, 1)} sec...")
        time.sleep(sleep_time)

    return None

# ==============================
# DATE
# ==============================

today = datetime.now()
formatted_date = today.strftime("%A – %d/%m/%Y")

# ==============================
# HELPERS
# ==============================

def strip_code_fences(text):
    text = text.strip()
    text = re.sub(r"^```(?:html)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

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
            intro_text = f"<p>{response.text.strip()}</p>"

except Exception as e:
    print(f"⚠️ AI intro failed: {e}")

# ==============================
# SCRAPE BETENSURED TIPS
# ==============================

BETENSURED_URL = "https://www.betensured.com/"

page_html = fetch_html(BETENSURED_URL, must_contain="expert-picks-table")

if not page_html:
    print("❌ Could not fetch betensured.com (likely Cloudflare blocking). Aborting without posting.")
    raise SystemExit(1)

soup = BeautifulSoup(page_html, "html.parser")

table = soup.find("table", class_="expert-picks-table")

matches = []

if table:
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    available_rows = []

    for row in rows:
        # Skip locked (premium) rows
        if row.find("i", class_="fa-lock"):
            continue

        # Must have a .set-1 span (team name)
        if not row.find("span", class_="set-1"):
            continue

        available_rows.append(row)

    random.shuffle(available_rows)
    selected_rows = available_rows[:4]

    for row in selected_rows:
        try:
            league = ""
            teams = ""
            ft_result = ""
            expert_tip = ""
            stats_url = ""

            small_el = row.find("small")
            if small_el:
                league = small_el.get_text(strip=True)

            teams_el = row.find("span", class_="set-1")
            if teams_el:
                teams = teams_el.get_text(strip=True)

            link_el = row.find("a", href=True)
            if link_el:
                href = link_el.get("href", "")
                stats_url = href if href.startswith("http") else "https://www.betensured.com" + href

            tds = row.find_all("td")

            for td in tds:
                red_span = td.find("span", style=lambda s: s and "color: red" in s)
                if red_span:
                    b_tag = red_span.find("b")
                    if b_tag:
                        expert_tip = b_tag.get_text(strip=True)
                    break

            if len(tds) >= 2:
                b_tag = tds[1].find("b")
                if b_tag:
                    ft_result = b_tag.get_text(strip=True)

            search_query = quote_plus(teams + " result")

            result_link = (
                f'<a href="https://www.google.com/search?q={search_query}" '
                f'target="_blank">Check</a>'
            )

            stats_link = (
                f'<a href="{stats_url}" target="_blank">Stats</a>'
                if stats_url else ""
            )

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
    print("❌ No matches scraped from betensured.com. Aborting without posting.")
    raise SystemExit(1)

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
- Output raw HTML only, no markdown code fences
- Use HTML format:

<h4>Team vs Team</h4>
<p>analysis...</p>
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        if hasattr(response, "text") and response.text:
            raw_html = strip_code_fences(response.text)

            analysis_soup = BeautifulSoup(raw_html, "html.parser")

            accordion_html = '<div class="accordion">'

            items = analysis_soup.find_all(["h4", "p"])

            for i in range(0, len(items), 2):
                title = items[i]
                content = items[i + 1] if i + 1 < len(items) else None

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

links_html = ""

try:
    resp = session.get(GITHUB_LINKS_URL, timeout=20)
    resp.raise_for_status()

    all_links = [
        line.strip()
        for line in resp.text.splitlines()
        if line.strip()
    ]

    selected_links = random.sample(all_links, min(3, len(all_links)))

    links_html = "<br>".join([
        f'<a href="{link}" target="_blank">{link}</a>'
        for link in selected_links
    ])

except Exception as e:
    print(f"⚠️ Could not load links: {e}")

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

if links_html:
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

class BrowserTransport(xmlrpc.client.SafeTransport):
    user_agent = BROWSER_UA


post_data = {
    "title": f"Soccer predictions today, {formatted_date}",
    "description": html,
    "categories": ["Football Predictions"],
}

post_id = None

for attempt in range(1, 4):
    try:
        wp_client = xmlrpc.client.ServerProxy(
            WP_XMLRPC, transport=BrowserTransport()
        )

        post_id = wp_client.metaWeblog.newPost(
            "",
            USERNAME,
            PASSWORD,
            post_data,
            True
        )

        print(f"✅ Post created successfully! ID: {post_id}")
        break

    except Exception as e:
        print(f"⚠️ Post attempt {attempt} failed: {e}")
        if attempt < 3:
            time.sleep(10 * attempt)

if post_id is None:
    print("❌ Failed to create post after retries")
    raise SystemExit(1)
