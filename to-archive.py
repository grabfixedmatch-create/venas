import requests
import os
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
import random

wp_url = "https://grabfixedmatch.com/wp-json/wp/v2/posts"
post_id = 397
username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD")

# ✅ Venasbet category ID
VENASBET_CATEGORY_ID = 3764

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

rows = soup.find_all("tr", class_="table-data__stats-parent")
filtered_rows = []

for row in rows:
    bold_span = row.find("span", class_="font-bold")
    if bold_span:
        filtered_rows.append(row)

matches = []
for row in filtered_rows:
    teams = [span.get_text(strip=True) for span in row.select("span.team")]
    if len(teams) < 2:
        continue

    game_name = f"{teams[0]} - {teams[1]}"

    score_tag = row.select_one("span.colored-value--score")
    score = score_tag.get_text(strip=True) if score_tag else None

    winner_odd_tag = row.find("div", style=lambda v: v and "font-weight: bold;" in v)
    winner_odd_raw = winner_odd_tag.get_text(strip=True) if winner_odd_tag else None

    if not winner_odd_raw:
        continue

    winner_odd = american_to_decimal(winner_odd_raw)
    if winner_odd is None:
        continue

    matches.append({
        "game": game_name,
        "score": score,
        "winner_odd": winner_odd
    })

valid_matches = []
for m in matches:
    if not m["score"] or not m["winner_odd"]:
        continue

    try:
        home_goals, away_goals = [int(x.strip()) for x in m["score"].split("-")]
        odd = float(m["winner_odd"])
    except ValueError:
        continue

    if home_goals == away_goals:
        continue

    if 2.30 <= odd <= 3.50:
        valid_matches.append(m)

if not valid_matches:
    print("No valid matches found")
    exit(0)

random_match = random.choice(valid_matches)

home_team, away_team = [t.strip() for t in random_match['game'].split(" - ")]
home_goals, away_goals = [int(s.strip()) for s in random_match['score'].split("-")]

score_clean = random_match['score'].replace(" ", "")

if home_goals > away_goals:
    tip_text = "1 (Home Win)"
    winner_side = "home"
elif away_goals > home_goals:
    tip_text = "2 (Away Win)"
    winner_side = "away"
else:
    tip_text = "X (Draw)"
    winner_side = "draw"

yesterday = (datetime.today() - timedelta(days=1)).strftime("%d.%m.%Y")

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

# --- Fetch existing post ---
response = requests.get(f"{wp_url}/{post_id}", auth=HTTPBasicAuth(username, app_password))
response.raise_for_status()
post_data = response.json()
current_content = post_data["content"]["rendered"]

container_start = '<div id="daily" class="card_parent card_parent_is--vip">'
if container_start in current_content:
    new_content = current_content.replace(container_start, container_start + "\n" + html_output)
else:
    new_content = html_output + "\n" + current_content

# --- Preserve existing categories and add Venasbet ---
existing_categories = post_data.get("categories", [])

if VENASBET_CATEGORY_ID not in existing_categories:
    existing_categories.append(VENASBET_CATEGORY_ID)

update_payload = {
    "content": new_content,
    "categories": existing_categories
}

# --- Update post ---
response = requests.post(
    f"{wp_url}/{post_id}",
    json=update_payload,
    auth=HTTPBasicAuth(username, app_password)
)

if response.status_code in [200, 201]:
    print(f"✅ Post {post_id} updated successfully!")
    resp_json = response.json()
    print("Updated post link:", resp_json.get("link"))
else:
    print("❌ Failed to update post:", response.status_code)
    print(response.text)
