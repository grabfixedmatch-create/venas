import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
import requests
import os

# ---------------- CONFIG ----------------
today = datetime.now()
formatted_date = today.strftime("%d.%m.%Y")
wp_url = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD")
category_id = 349 

url = "https://zakabet.com/over-2-5-goals"
scraper = cloudscraper.create_scraper()  # bypass Cloudflare
html = scraper.get(url).text

soup = BeautifulSoup(html, "html.parser")
sections = soup.find_all("section", class_="match-section")

matches = []
tags_to_add = []

# Filter threshold
threshold = 74

for section in sections:
    section_matches = section.find_all("li", class_="match-item")
    for match in section_matches:
        # Teams
        teams = [t.get_text(strip=True) for t in match.select(".team-name")]
        if len(teams) == 2:
            match_name = f"{teams[0]} VS {teams[1]}"
            team1, team2 = teams
        else:
            match_name = "Unknown Match"
            team1 = team2 = "Unknown"

        # Tip
        tip_elem = match.find("p", class_="picks-value")
        tip_text = tip_elem.get_text(" ", strip=True).replace("Tip:", "").strip().upper() if tip_elem else "N/A"

        # Probability
        prob_elem = match.find("p", class_="scores-value")
        prob = float(prob_elem.get_text(strip=True)) if prob_elem else 0.0

        # Include if probability > threshold
        if prob > threshold:
            # Google search link
            search_query = match_name.replace(" ", "+")
            result_link = f'<a href="https://www.google.com/search?q={search_query}+result+{formatted_date}" target="_blank">Check</a>'

            matches.append({
                "date": formatted_date,
                "teams": match_name,
                "tip": tip_text,
                "result": result_link,
                "team1": team1,
                "team2": team2
            })

# If no matches found, reduce threshold to 71%
if not matches:
    threshold = 71
    for section in sections:
        section_matches = section.find_all("li", class_="match-item")
        for match in section_matches:
            teams = [t.get_text(strip=True) for t in match.select(".team-name")]
            if len(teams) == 2:
                match_name = f"{teams[0]} VS {teams[1]}"
                team1, team2 = teams
            else:
                match_name = "Unknown Match"
                team1 = team2 = "Unknown"

            tip_elem = match.find("p", class_="picks-value")
            tip_text = tip_elem.get_text(" ", strip=True).replace("Tip:", "").strip().upper() if tip_elem else "N/A"
            prob_elem = match.find("p", class_="scores-value")
            prob = float(prob_elem.get_text(strip=True)) if prob_elem else 0.0

            if prob > threshold:
                search_query = match_name.replace(" ", "+")
                result_link = f'<a href="https://www.google.com/search?q={search_query}+result+{formatted_date}" target="_blank">Check</a>'

                matches.append({
                    "date": formatted_date,
                    "teams": match_name,
                    "tip": tip_text,
                    "result": result_link,
                    "team1": team1,
                    "team2": team2
                })

# ---------------- BUILD HTML TABLE ----------------
html_table = """
<table id="free-tip">
    <thead>
        <tr>
            <th>Date</th>
            <th>Match</th>
            <th>Tip</th>
            <th>Check</th>
        </tr>
    </thead>
    <tbody>
"""

for m in matches:
    html_table += f"""
        <tr>
            <td>{m['date']}</td>
            <td>{m['teams']}</td>
            <td>{m['tip']}</td>
            <td>{m['result']}</td>
        </tr>
    """

html_table += """
    </tbody>
</table>
"""

tag_ids = []

for m in matches:
    t1 = m["team1"]
    t2 = m["team2"]
    tags_to_add = [
        f"{t1} vs {t2} goals prediction",
        f"{t1} Over 2.5 goals soccer predictions",
        f"{t2} Over 2.5 goals soccer predictions"
    ]

    for tag_name in tags_to_add:
        response = requests.get(
            f"https://grabfixedmatch.com/wp-json/wp/v2/tags?search={tag_name}",
            auth=HTTPBasicAuth(username, app_password)
        )
        response.raise_for_status()
        data = response.json()

        if data:
            tag_ids.append(data[0]["id"])
        else:
            response = requests.post(
                "https://grabfixedmatch.com/wp-json/wp/v2/tags",
                auth=HTTPBasicAuth(username, app_password),
                json={"name": tag_name}
            )
            response.raise_for_status()
            tag_ids.append(response.json()["id"])

# ---------------- POST TO WORDPRESS ----------------
post_title = f"⚽ Over 2.5 Goals Predictions - {formatted_date}"

post_data = {
    "title": post_title,
    "content": html_table,
    "status": "publish",
    "categories": [category_id],
    "tags": tag_ids
}

response = requests.post(
    wp_url,
    json=post_data,
    auth=HTTPBasicAuth(username, app_password)
)

if response.status_code == 201:
    print("✅ Post created successfully!")
else:
    print("❌ Failed to create post:", response.text)
