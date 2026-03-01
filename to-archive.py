import requests
import os
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
# import random

wp_url = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
post_id = 397
username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD")

def fetch_with_retries(url, retries=5, delay=5):
    """Fetch URL with retries and delay in case the content is not ready."""
    for i in range(retries):
        response = requests.get(url, timeout=20)
        if response.status_code == 200 and "table-data__table" in response.text:
            return response
        print(f"⚠️ Attempt {i+1} failed, retrying in {delay} sec...")
        time.sleep(delay)
    response.raise_for_status()
    return response

def american_to_decimal(odd):
    """Convert American odds to decimal odds."""
    odd = str(odd).replace(",", "").strip()
    if odd in ["-", ""]:
        return None
    try:
        odd = int(odd)
    except ValueError:
        return None
    if odd > 0:
        return round((odd / 100) + 1, 2)
    else:
        return round((100 / abs(odd)) + 1, 2)


today = datetime.now()
day_name = today.strftime("%A")
formatted_date = today.strftime("%A - %d/%m/%Y")

url = "https://redscores.com/football/yesterday-results"

response = fetch_with_retries(url, retries=5, delay=10)

soup = BeautifulSoup(response.text, "html.parser")

table = soup.find_all("table", class_="table-data__table table-data__table wide animate-collapsing")

rows = soup.find_all("tr", class_="table-data__stats-parent")
filtered_rows = []

for row in rows:
    bold_span = row.find("span", class_="font-bold")
    if bold_span:
        filtered_rows.append(row)

first_row = filtered_rows[0]

# Extract structured data
matches = []
for row in filtered_rows:
    teams = [span.get_text(strip=True) for span in row.select("span.team")]
    game_name = f"{teams[0]} - {teams[1]}" if len(teams) >= 2 else None

    score_tag = row.select_one("span.colored-value--score")
    score = score_tag.get_text(strip=True) if score_tag else None

    winner_odd_tag = row.find("div", style=lambda v: v and "font-weight: bold;" in v)
    winner_odd_raw = winner_odd_tag.get_text(strip=True) if winner_odd_tag else None

    if not winner_odd_raw:
        continue  # skip rows without odds

    winner_odd = american_to_decimal(winner_odd_raw)
    if winner_odd is None:
        continue  # skip rows that could not be converted

    matches.append({
        "game": game_name,
        "score": score,
        "winner_odd": winner_odd
    })

print('Matches: ', matches)

valid_matches = []
for m in matches:
    if not m["score"] or not m["winner_odd"]:
        continue
    
    try:
        home_goals, away_goals = [int(x.strip()) for x in m["score"].split("-")]
        odd = float(m["winner_odd"])
    except ValueError:
        continue  # skip malformed rows

    # Only home win or away win
    if home_goals == away_goals:
        continue

    # Odd between 2.30 and 3.50
    if 2.30 <= odd <= 3.50:
        valid_matches.append(m)

print ('valid mathces', matches)

# Pick one random match
if valid_matches:
    random_match = random.choice(valid_matches)
else:
    print("No valid matches found")
    exit(0)

home_team, away_team = [t.strip() for t in random_match['game'].split(" - ")]

# Split score
home_goals, away_goals = [int(s.strip()) for s in random_match['score'].split("-")]

raw_score = random_match['score']
score_clean = raw_score.replace(" ", "")

# Determine tip
if home_goals > away_goals:
    tip_text = "1 (Home Win)"
    winner_side = "home"
elif away_goals > home_goals:
    tip_text = "2 (Away Win)"
    winner_side = "away"
else:
    tip_text = "X (Draw)"
    winner_side = "draw"

# Today’s date
yesterday = (datetime.today() - timedelta(days=1)).strftime("%d.%m.%Y")

# Build HTML
html_output = f"""
<div class="card_wrap">
    <div class="daily_match">
        <div class="daily_match_header"><span class="highlighted">{yesterday}</span> &nbsp; MATCH+</div>
        <div class="daily_match_data">
            <div class="match">{home_team} vs {away_team}</div>
            <ul class="match_tip_data">
                <li>Tip: {tip_text}</li>
                <li>Odds: {random_match['winner_odd']}</li>
                <li>Win possibility: 100%</li>
            </ul>
        </div>
        <div class="daily_match_footer">
            <div class="daily_match_score">{score_clean}</div>
            <div class="daily_match_score_explanation">The {winner_side} side claimed the win</div>
        </div>
    </div>
</div>
"""

response = requests.get(f"{wp_url}/{post_id}", auth=HTTPBasicAuth(username, app_password))
response.raise_for_status()
post_data = response.json()
current_content = post_data["content"]["rendered"]  # raw content

container_start = '<div id="daily" class="card_parent card_parent_is--vip">'
if container_start in current_content:
    # Insert the new match HTML right after the opening tag
    new_content = current_content.replace(
        container_start,
        container_start + "\n" + html_output
    )
else:
    # Fallback: prepend at the very top if container not found
    new_content = html_output + "\n" + current_content

update_payload = {
    "content": new_content
}


response = requests.post(
    f"{wp_url}/{post_id}",  # include post ID
    json=update_payload,     # <-- send the updated content here
    auth=HTTPBasicAuth(username, app_password)
)

# --- Check response ---
if response.status_code in [200, 201]:
    print(f"Post {post_id} updated successfully!")
    resp_json = response.json()
    print("Updated post link:", resp_json.get("link"))
else:
    print("Failed to update post:", response.status_code)
    print(response.text)
# if response.status_code == 201:
#     print("✅ Post created successfully!")
# else:
#     print("❌ Failed to create post:", response.text)
