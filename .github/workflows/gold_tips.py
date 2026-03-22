import cloudscraper
from bs4 import BeautifulSoup
import requests
from requests.auth import HTTPBasicAuth

# ---------------- CONFIG ----------------
URL = "https://eaglepredict.com/predictions/bet-of-the-day/"
WP_URL = "https://goldfixedmatches.com/wp-json/wp/v2/posts"
POST_ID = 207
USERNAME = "admin"
APP_PASSWORD = "ot23 QCqi HfMW nACD 8SLV SoQK"

# ---------------- SCRAPE ----------------
scraper = cloudscraper.create_scraper()
html = scraper.get(URL).text
soup = BeautifulSoup(html, "html.parser")

sections = soup.select("div.row-start-1.col-start-1")

rows_html = []

for section in sections:
    try:
        league = section.select_one(".p-4 span").get_text(strip=True)
        league_logo = section.select_one(".p-4 img")["src"]

        time_date = section.select(".p-4 p")
        time_ = time_date[0].get_text(strip=True) if len(time_date) > 0 else ""
        date_ = time_date[1].get_text(strip=True) if len(time_date) > 1 else ""

        teams = section.select(".grid.grid-cols-4 > div")
        if len(teams) < 3:
            continue

        home = teams[0].select_one("p").get_text(strip=True)
        away = teams[2].select_one("p").get_text(strip=True)

        home_logo = teams[0].select_one("img")["src"]
        away_logo = teams[2].select_one("img")["src"]

        prediction = section.select_one(".bg-base-300").get_text(strip=True)

        row = f"""
<tr>
<td>
    <span style="display:block;">{date_}</span>
    <span style="display:block; font-size:12px;">{time_}</span>
</td>

<td>
    <span style="display:inline-flex; align-items:center;">
        <img src="{home_logo}" width="18" style="margin-right:4px;">
        {home}
    </span>

    <span style="margin:0 6px;">vs</span>

    <span style="display:inline-flex; align-items:center;">
        <img src="{away_logo}" width="18" style="margin-right:4px;">
        {away}
    </span>
</td>

<td></td>

<td><strong>{prediction}</strong></td>

<td>
    <img src="{league_logo}" width="20" title="{league}">
</td>
</tr>
"""
        rows_html.append(row)

    except Exception as e:
        print("Skipping:", e)

# ---------------- FETCH POST ----------------
response = requests.get(
    f"{WP_URL}/{POST_ID}",
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
)

if response.status_code != 200:
    raise Exception(f"Failed to fetch post: {response.status_code} - {response.text}")

post_data = response.json()
content = post_data.get("content", {}).get("rendered", "")

# ---------------- PARSE TABLE ----------------
soup = BeautifulSoup(content, "html.parser")

# IMPORTANT: table is inside figure
figure = soup.find("figure", class_="wp-block-table")
if not figure:
    raise Exception("Figure not found")

table = figure.find("table", id="soccer-predictions-table")
if not table:
    raise Exception("Table not found")

tbody = table.find("tbody")
if not tbody:
    raise Exception("tbody not found")

# ---------------- REPLACE ROWS ----------------
tbody.clear()

for row_html in rows_html:
    tbody.append(BeautifulSoup(row_html, "html.parser"))

# ---------------- UPDATE POST ----------------
updated_html = str(soup)

update_response = requests.post(
    f"{WP_URL}/{POST_ID}",
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
    json={"content": updated_html}
)

if update_response.status_code == 200:
    print("✅ Post updated successfully!")
else:
    print(f"❌ Failed: {update_response.status_code}")
    print(update_response.text)
