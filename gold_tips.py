import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
import cloudscraper
from datetime import datetime
import os

# ---------------- CONFIG ----------------
WP_URL = "https://goldfixedmatches.com/wp-json/wp/v2/posts"
POST_ID = 207
USERNAME = "admin"
APP_PASSWORD = "ot23 QCqi HfMW nACD 8SLV SoQK"

SCRAPE_URL = "https://eaglepredict.com/predictions/bet-of-the-day/"

if not USERNAME or not APP_PASSWORD:
    raise ValueError("Missing WP credentials")

# ---------------- SCRAPING ----------------
scraper = cloudscraper.create_scraper()
html = scraper.get(SCRAPE_URL).text

soup = BeautifulSoup(html, "html.parser")
sections = soup.find_all("div", class_="row-start-1 col-start-1")

rows_html = []

for section in sections:
    try:
        league = section.select_one(".flex.items-center.gap-2 span").text.strip()
        time_ = section.select_one(".flex.items-center.gap-2 p").text.strip()
        date_ = section.select(".flex.items-center.gap-2 p")[1].text.strip()

        home = section.select("div.grid-cols-4 div")[0].p.text.strip()
        home_logo = section.select("div.grid-cols-4 div img")[0]["src"]

        away = section.select("div.grid-cols-4 div")[2].p.text.strip()
        away_logo = section.select("div.grid-cols-4 div img")[2]["src"]

        prediction = section.select_one("div.bg-base-300").text.strip()

        # -------- LEAGUE FLAG (simple mapping) --------
        league_logo = "https://flagcdn.com/w20/un.png"
        if "Bosnia" in league:
            league_logo = "https://flagcdn.com/w20/ba.png"
        elif "South Africa" in league or "Premier Soccer League" in league:
            league_logo = "https://flagcdn.com/w20/za.png"

        # -------- ROW HTML --------
        row = f"""
<tr>
    <td>
        <span style="display:block;">{date_}</span>
        <span style="display:block; font-size:12px; opacity:0.8;">{time_}</span>
    </td>

    <td>
        <span style="display:inline-flex; align-items:center; margin-right:6px;">
            <img src="{home_logo}" width="18" style="margin-right:4px;">
            {home}
        </span>

        <span style="margin: 0 6px;">vs</span>

        <span style="display:inline-flex; align-items:center; margin-left:6px;">
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

# ---------------- FETCH WORDPRESS POST ----------------
response = requests.get(
    f"{WP_URL}/{POST_ID}",
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD)
)

if response.status_code != 200:
    raise Exception(f"Failed to fetch post: {response.status_code} - {response.text}")

post_data = response.json()
content = post_data.get("content", {}).get("rendered", "")

soup = BeautifulSoup(content, "html.parser")

# IMPORTANT: target by ID (your case)
table = soup.find("table", id="soccer-predictions-table")
if not table:
    raise Exception("Table not found")

tbody = table.find("tbody")
if not tbody:
    raise Exception("No tbody found")

# ---------------- INSERT ROWS AT TOP ----------------
for row_html in reversed(rows_html):
    tbody.insert(0, BeautifulSoup(row_html, "html.parser"))

# ---------------- UPDATE POST ----------------
updated_html = str(soup)

update_response = requests.post(
    f"{WP_URL}/{POST_ID}",
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
    json={"content": updated_html}
)

if update_response.status_code == 200:
    print("Post updated successfully!")
else:
    print("Update failed:", update_response.status_code, update_response.text)
