import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
from urllib.parse import quote_plus
import random

# WordPress credentials
wp_url = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD")

# Date for post
today = datetime.now()
formatted_date = today.strftime("%A – %d/%m/%Y")

url = "https://www.venasbet.com/"
response = requests.get(url)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
table = soup.find("table", class_="table table-striped text-center mastro-tips")

matches = []
tags_to_add = []

if table:
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else []

    random.shuffle(rows)
    rows = rows[:4]

    for row in rows:
        cols = [td.get_text(strip=True, separator=" ") for td in row.find_all("td")]
        if len(cols) == 4:
            team_text = cols[2]

            # Build Google search link
            search_query = quote_plus(team_text + " result")
            result_link = f'<a href="https://www.google.com/search?q={search_query}" target="_blank">Check</a>'

            matches.append({
                "time": cols[0],
                "league": cols[1],
                "teams": team_text,
                "prediction": cols[3],
                "result": result_link,
            })

for match in matches:
    teams = match["teams"].replace("VS", "|").split("|")
    for team in teams:
        team = team.strip()
        if team:
            if team not in tags_to_add:
                tags_to_add.append(team)
            fixed_tag = f"{team} Fixed Matches"
            if fixed_tag not in tags_to_add:
                tags_to_add.append(fixed_tag)

github_txt_url = "https://raw.githubusercontent.com/grabfixedmatch-create/venas/main/football_links.txt"
response = requests.get(github_txt_url)
response.raise_for_status()
all_links = [line.strip() for line in response.text.splitlines() if line.strip()]

selected_links = random.sample(all_links, min(3, len(all_links)))
links_html = "<br>".join(f'<a href="{link}" target="_blank">{link}</a>' for link in selected_links)

html = """
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
            <td>{m['result']}</td>
        </tr>
    """

html += f"""
    </tbody>
</table>
<br>
<h3 class="links-per-post">Useful Links:</h3>
{links_html}
"""

# Ensure tags exist in WordPress
session = requests.Session()
tag_ids = []
for tag_name in tags_to_add:
    resp = session.get(
        f"https://grabfixedmatch.com/wp-json/wp/v2/tags?search={tag_name}",
        auth=HTTPBasicAuth(username, app_password)
    )
    resp.raise_for_status()
    data = resp.json()

    if data:
        tag_ids.append(data[0]["id"])
    else:
        resp = session.post(
            "https://grabfixedmatch.com/wp-json/wp/v2/tags",
            auth=HTTPBasicAuth(username, app_password),
            json={"name": tag_name}
        )
        resp.raise_for_status()
        tag_ids.append(resp.json()["id"])

post_data = {
    "title": f"⚽ Fixed matches predictions, {formatted_date}",
    "content": html,
    "status": "publish",
    "tags": tag_ids
}

response = session.post(wp_url, json=post_data, auth=HTTPBasicAuth(username, app_password))

if response.status_code == 201:
    print("✅ Post created successfully!")
else:
    print("❌ Failed to create post:", response.text)
