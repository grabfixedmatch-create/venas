import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
import os
import random
import requests

# ---------------- CONFIG ----------------
today = datetime.now()
formatted_date = today.strftime("%d.%m.%Y")

username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD_FOOTY")

# ---------------- SCRAPE FREE TIPS ----------------
url = "https://tipsbet.co.uk/"
scraper = cloudscraper.create_scraper()
html = scraper.get(url).text

soup = BeautifulSoup(html, "html.parser")
tables = soup.find_all("table")
table = tables[2]  # adjust if table index changes

rows = table.find_all("tr")
tip_rows = []

for row in rows:
    cols = row.find_all("td")
    if len(cols) == 9:
        result_text = cols[8].get_text(strip=True)
        if "background-color: #f4fcdf" in row.get("style", ""):
            continue  # skip VIP rows
        if result_text == "?":
            tip_rows.append(row)
    if len(tip_rows) == 4:  # take max 4 free tips
        break

if not tip_rows:
    print("No free tips found.")
    exit()

random.shuffle(tip_rows)
selected_rows = random.sample(tip_rows, min(2, len(tip_rows)))  # pick 2 rows randomly

# ---------------- BUILD TABLE ROWS ----------------
formatted_rows = []
today_str = datetime.now().strftime("%d.%m.%Y")

for row in selected_rows:
    cols = row.find_all("td")
    teams = cols[5].get_text(strip=True).split("–")  # en dash
    team1 = teams[0].strip()
    team2 = teams[1].strip()
    tip = cols[6].get_text(strip=True)
    
    new_row = f"""
    <tr>
      <td>{today_str}</td>
      <td class="match">
        <div>{team1}</div>
        <div>vs</div>
        <div>{team2}</div>
      </td>
      <td>{tip}</td>
      <td><span class=""></span></td>
    </tr>
    """
    formatted_rows.append(new_row)

# ---------------- CREATE FULL TABLE ----------------
table_html = f"""
<table class="tips-table" id="footy-free-tips">
    <thead>
        <tr>
            <th>Date</th>
            <th>Match</th>
            <th>Tip</th>
            <th>Outcome</th>
        </tr>
    </thead>
    <tbody>
        {''.join(formatted_rows)}
    </tbody>
</table>
"""

# ---------------- FETCH RANDOM TITLE AND TAGS ----------------
posts_url = "https://raw.githubusercontent.com/grabfixedmatch-create/venas/main/footy_post_titles_keywords_unique.txt"
tags_url = "https://raw.githubusercontent.com/grabfixedmatch-create/venas/main/footy_post_tags_keywords_unique.txt"

titles = requests.get(posts_url).text.splitlines()
tags_list = requests.get(tags_url).text.splitlines()

post_title = random.choice([t.strip() for t in titles if t.strip()])
selected_tags = random.sample([t.strip() for t in tags_list if t.strip()], 5)

# ---------------- ENSURE TAGS EXIST IN WORDPRESS ----------------
session = requests.Session()
tag_ids = []

for tag_name in selected_tags:
    resp = session.get(
        f"https://footy1x2.info/wp-json/wp/v2/tags?search={tag_name}",
        auth=HTTPBasicAuth(username, app_password)
    )
    resp.raise_for_status()
    data = resp.json()

    if data:
        tag_ids.append(data[0]["id"])
    else:
        resp = session.post(
            "https://footy1x2.info/wp-json/wp/v2/tags",
            auth=HTTPBasicAuth(username, app_password),
            json={"name": tag_name}
        )
        resp.raise_for_status()
        tag_ids.append(resp.json()["id"])

# ---------------- CREATE NEW WORDPRESS POST ----------------
wp_url = 'https://footy1x2.info/wp-json/wp/v2/posts'
post_data = {
    "title": post_title,
    "content": table_html,
    "status": "publish",
    "tags": tag_ids
}

response = session.post(
    wp_url,
    auth=HTTPBasicAuth(username, app_password),
    json=post_data
)

if response.status_code in [200, 201]:
    print("✅ New post created successfully!")
else:
    print("❌ Failed to create post:", response.status_code, response.text)
