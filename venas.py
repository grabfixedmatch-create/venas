import requests
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth

wp_url = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
username = "pettarr97@gmail.com"
app_password = "NOfC cNK5 M1le lvvY HfEZ FqhU"

today = datetime.now()
day_name = today.strftime("%A")
formatted_date = today.strftime("%A - %d/%m/%Y")

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

    for row in rows:
        cols = [td.get_text(strip=True, separator=" ") for td in row.find_all("td")]
        if len(cols) == 4:
            match = {
                "time": cols[0],
                "league": cols[1],
                "teams": cols[2],
                "prediction": cols[3],
            }
            matches.append(match)



for match in matches:
    teams = match["teams"].replace("VS", "|").split("|")
    for team in teams:
        team = team.strip()
        if team:
            # Original team tag
            if team not in tags_to_add:
                tags_to_add.append(team)
            # "Fixed Matches" variant
            fixed_tag = f"{team} Fixed Matches"
            if fixed_tag not in tags_to_add:
                tags_to_add.append(fixed_tag)

html = """
<table id="free-tip">
    <thead>
        <tr>
            <th>Time</th>
            <th>League</th>
            <th>Teams</th>
            <th>Prediction</th>
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
            <td></td>
        </tr>
    """

html += """
    </tbody>
</table>
"""

tag_ids = []
for tag_name in tags_to_add:
    response = requests.get(f"https://grabfixedmatch.com/wp-json/wp/v2/tags?search={tag_name}", auth=HTTPBasicAuth(username, app_password))
    response.raise_for_status()
    data = response.json()
    
    if data:
        # Tag exists, get its ID
        tag_ids.append(data[0]["id"])
    else:
        # Tag doesn't exist, create it
        response = requests.post(
            f"https://grabfixedmatch.com/wp-json/wp/v2/tags",
            auth=HTTPBasicAuth(username, app_password),
            json={"name": tag_name}
        )
        response.raise_for_status()
        tag_ids.append(response.json()["id"])

post_data = {
    "title": f"⚽ Fixed matches predictions, {formatted_date}",
    "content": html,
    "status": "publish",
    "tags": tag_ids
}

response = requests.post(
    wp_url,
    json=post_data,
    auth=HTTPBasicAuth(username, app_password)
)

if response.status_code == 201:
    print("Post created successfully!")
else:
    print("Failed to create post:", response.text)
