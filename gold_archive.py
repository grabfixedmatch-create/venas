import random
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import xmlrpc.client

# ---------------- CONFIG ----------------
URL = "https://www.soccersite.com/yesterday-football-predictions"

WP_XMLRPC = "https://goldfixedmatches.com/xmlrpc.php"
POST_ID = 474
USERNAME = "admin"
PASSWORD = "ot23 QCqi HfMW nACD 8SLV SoQK"

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
    games = grid.find_all('a', class_='eachgame')[:50]

    for game in games:
        try:
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

            if predicted_tip and final_score and odds and 2.0 <= odds <= 2.5:
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

        except:
            continue

# ---------------- SELECT 1 MATCH ----------------
if not matches_data:
    raise Exception("No matches found!")

win_matches = [m for m in matches_data if m['result'] == 'WIN']
lose_matches = [m for m in matches_data if m['result'] == 'LOSE']

if lose_matches and random.random() < 0.1:
    selected_match = random.choice(lose_matches)
elif win_matches:
    selected_match = random.choice(win_matches)
else:
    selected_match = random.choice(matches_data)

# ---------------- FORMAT DATA ----------------
home = selected_match['home_team']
away = selected_match['away_team']
tip_raw = selected_match['predicted_tip']
result = selected_match['result']
score = selected_match['final_score']

if tip_raw == '1':
    tip_text = home
elif tip_raw == '2':
    tip_text = away
elif tip_raw.upper() == 'X':
    tip_text = "Draw"
else:
    tip_text = tip_raw

formatted_date = datetime.strptime(
    selected_match['date'],
    '%Y-%m-%d %H:%M'
).strftime('%d.%m.%Y')

# ---------------- GENERATE TABLE ROW ----------------
new_row_html = f"""
<tr>
    <td>{formatted_date}</td>
    <td class="match">
        <div>{home}</div>
        <div>vs</div>
        <div>{away}</div>
    </td>
    <td>{score}</td>
    <td><span class="{'win' if result=='WIN' else 'lose'}">{tip_text}</span></td>
</tr>
"""

# ---------------- WORDPRESS XML-RPC ----------------
client = xmlrpc.client.ServerProxy(WP_XMLRPC)

# Get existing post
post = client.wp.getPost(0, USERNAME, PASSWORD, POST_ID)
content = post['post_content']

soup = BeautifulSoup(content, "html.parser")

table = soup.find("table", {"id": "daily-archive-table"})
if not table:
    raise Exception("Table with id 'daily-archive-table' not found")

# Handle your double tbody structure
tbodies = table.find_all("tbody")

if len(tbodies) < 2:
    raise Exception("Expected 2 tbody elements (your HTML structure is invalid)")

data_tbody = tbodies[1]  # second tbody is where rows go

# Insert new row at TOP
data_tbody.insert(0, BeautifulSoup(new_row_html, "html.parser"))

updated_content = str(soup)

# Update post
client.wp.editPost(0, USERNAME, PASSWORD, POST_ID, {
    'post_content': updated_content
})

print("✅ Match added successfully at top of table!")
