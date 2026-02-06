import random
from datetime import datetime
# from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import requests
from requests.auth import HTTPBasicAuth
import os

# ---------------- CONFIG ----------------
URL = "https://www.soccersite.com/yesterday-football-predictions"
WP_URL = "https://footy1x2.info/wp-json/wp/v2/posts"
POST_ID = 77
USERNAME = os.environ.get("WP_USERNAME")
APP_PASSWORD = os.environ.get("WP_APP_PASSWORD_FOOTY")

if not USERNAME or not APP_PASSWORD:
    raise ValueError("WP_USERNAME and WP_APP_PASSWORD_FOOTY must be set in environment variables.")

# ---------------- SCRAPING ----------------
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL)
    page.wait_for_selector(".eachgame")
    html = page.content()
    browser.close()

# ---------------- PARSING ----------------
soup = BeautifulSoup(html, "html.parser")
matches_data = []

predictions = soup.find_all('div', class_='grid topgrid')
for grid in predictions:
    games = grid.find_all('a', class_='eachgame')[:50]  # first 50 games
    for game in games:
        home_team = game.find('div', itemprop='homeTeam').find('span', itemprop='name').text
        away_team = game.find('div', itemprop='awayTeam').find('span', itemprop='name').text
        date = game.find('div', class_='datetip')['content']
        tip_div = game.find('div', class_='nostartip')
        predicted_tip = tip_div.text.strip() if tip_div else None
        prediscore_div = game.find('div', class_='prediscore')
        final_score = None
        if prediscore_div:
            scoreline_div = prediscore_div.find('div', class_='scoreline')
            if scoreline_div:
                final_score = scoreline_div.text.strip()
        odds_div = game.find('div', class_='prediodd').find('div')
        odds = float(odds_div.text) if odds_div else None

        if predicted_tip and final_score and 1.7 <= odds <= 2.2:
            # Determine WIN/LOSE
            try:
                home_score, away_score = map(int, final_score.split('-'))
                if predicted_tip == '1':
                    result = "WIN" if home_score > away_score else "LOSE"
                elif predicted_tip == '2':
                    result = "WIN" if away_score > home_score else "LOSE"
                elif predicted_tip.upper() == 'X':
                    result = "WIN" if home_score == away_score else "LOSE"
                else:
                    result = "LOSE"
            except:
                result = "LOSE"

            matches_data.append({
                'home_team': home_team,
                'away_team': away_team,
                'date': date,
                'predicted_tip': predicted_tip,
                'final_score': final_score,
                'odds': odds,
                'result': result
            })

# ---------------- SELECT MATCHES ----------------
num_matches = 2 if random.randint(1, 10) <= 9 else 1
win_matches = [m for m in matches_data if m['result'] == 'WIN']
lose_matches = [m for m in matches_data if m['result'] == 'LOSE']

selected_matches = []
for _ in range(num_matches):
    if lose_matches and random.random() < 0.1:
        selected = random.choice(lose_matches)
        lose_matches.remove(selected)
    elif win_matches:
        selected = random.choice(win_matches)
        win_matches.remove(selected)
    else:
        selected = random.choice(matches_data)
    selected_matches.append(selected)

# ---------------- GENERATE HTML TRs ----------------
formatted_rows = []
for match in selected_matches:
    home, away = match['home_team'], match['away_team']
    tip_raw, result = match['predicted_tip'], match['result']

    # Show team names in Tip column
    if tip_raw == '1':
        tip_text = home
    elif tip_raw == '2':
        tip_text = away
    elif tip_raw.upper() == 'X':
        tip_text = "Draw"
    else:
        tip_text = tip_raw

    formatted_rows.append(f"""
<tr>
    <td>{datetime.strptime(match['date'], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y')}</td>
    <td class="match">
        <div>{home}</div>
        <div>vs</div>
        <div>{away}</div>
    </td>
    <td>{tip_text}</td>
    <td><span class="{'win' if result=='WIN' else 'lose'}">{result}</span></td>
</tr>
""")

# ---------------- FETCH WORDPRESS POST ----------------
response = requests.get(f"{WP_URL}/{POST_ID}", auth=HTTPBasicAuth(USERNAME, APP_PASSWORD))
if response.status_code != 200:
    raise Exception(f"Failed to fetch post: {response.status_code}")

post_data = response.json()
current_content = post_data.get("content", {}).get("rendered", "")

soup = BeautifulSoup(current_content, "html.parser")
table = soup.find("table", class_="tips-table")
if not table:
    raise Exception("No table with class 'tips-table' found in post content")

tbody = table.find("tbody")
if not tbody:
    raise Exception("No <tbody> found in the table")

# ---------------- INSERT NEW ROWS AT THE TOP ----------------
for row_html in reversed(formatted_rows):
    new_row = BeautifulSoup(row_html, "html.parser")
    tbody.insert(0, new_row)

# ---------------- UPDATE WORDPRESS POST ----------------
updated_html = str(soup)
update_response = requests.post(
    f"{WP_URL}/{POST_ID}",
    auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
    json={"content": updated_html}
)

if update_response.status_code == 200:
    print("Post updated successfully!")
else:
    print(f"Failed to update post: {update_response.status_code} - {update_response.text}")
