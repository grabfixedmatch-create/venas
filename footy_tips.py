import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
import os
import requests
import random

# ---------------- CONFIG ----------------
today = datetime.now()
formatted_date = today.strftime("%d.%m.%Y")

# WordPress credentials from environment variables
username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD_FOOTY")

if not username or not app_password:
    raise ValueError("WP_USERNAME and WP_APP_PASSWORD must be set in environment variables.")

url = "https://tipsbet.co.uk/"
scraper = cloudscraper.create_scraper()  # bypass Cloudflare
html = scraper.get(url).text

soup = BeautifulSoup(html, "html.parser")
tables = soup.find_all("table")

table = tables[2]

rows = table.find_all("tr")
tip_rows = []

for row in rows:
    cols = row.find_all("td")
    if len(cols) == 9:
        result_text = cols[8].get_text(strip=True)
        # skip VIP rows by background-color if needed
        if "background-color: #f4fcdf" in row.get("style", ""):
            continue
        if result_text == "?":
            tip_rows.append(row)
    if len(tip_rows) == 4:
        break

if not tip_rows:
    print("No free tips found.")
else:
    random.shuffle(tip_rows)
    selected_rows = random.sample(tip_rows, min(2, len(tip_rows)))

formatted_rows = []

today_str = datetime.now().strftime("%d.%m.%Y")

for row in selected_rows:
    cols = row.find_all("td")
    # Extract team names
    teams = cols[5].get_text(strip=True).split("–")  # note: en dash
    team1 = teams[0].strip()
    team2 = teams[1].strip()
    
    # Extract tip
    tip = cols[6].get_text(strip=True)
    
    # Build new row
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

wp_url = 'https://footy1x2.info/wp-json/wp/v2/posts'
post_data = {
    "title": f"Free Tips - {formatted_date}",  # you can later pick a random title from file
    "content": table_html,
    "status": "publish"
}

response = scraper.post(
    wp_url,
    auth=HTTPBasicAuth(username, app_password),
    json=post_data
)

if response.status_code in [200, 201]:
    print("✅ New post created successfully!")
else:
    print("❌ Failed to create post:", response.status_code, response.text)
