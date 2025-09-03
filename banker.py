import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
import os
import requests

# ---------------- CONFIG ----------------
today = datetime.now()
formatted_date = today.strftime("%A - %d/%m/%Y")

# WordPress credentials from environment variables
username = os.environ.get("WP_USERNAME")
app_password = os.environ.get("WP_APP_PASSWORD")

if not username or not app_password:
    raise ValueError("WP_USERNAME and WP_APP_PASSWORD must be set in environment variables.")

# ---------------- SCRAPE BANKER OF THE DAY ----------------
url = "https://bankerpredict.com/banker-of-the-day"
scraper = cloudscraper.create_scraper()  # bypass Cloudflare
html = scraper.get(url).text

soup = BeautifulSoup(html, "html.parser")
tables = soup.find_all("table", class_="table table-striped myTableSmall")

if len(tables) < 2:
    print("Error: Table not found. Check HTML snippet:")
    print(html[:1000])
    exit()

table = tables[0]

# Extract rows
rows = table.find("tbody").find_all("tr")
output_rows = ""
for row in rows:
    cols = row.find_all("td")
    # Instead of using scraped time, show today's date
    date_str = today.strftime("%d.%m.%Y")
    league = cols[1].get_text(strip=True)
    match = cols[2].get_text(" ", strip=True)
    tip = cols[3].get_text(strip=True).upper()  # Tip in uppercase

    search_url = f"https://www.google.com/search?q={match.replace(' ', '+')}+result"
    output_rows += f"""
<tr>
    <td>{date_str}</td>
    <td>{league}</td>
    <td>{match}</td>
    <td>{tip}</td>
    <td><a href="{search_url}" target="_blank">Check</a></td>
</tr>
"""

# ---------------- FETCH WORDPRESS PAGE ----------------
wp_url = 'https://grabfixedmatch.com/wp-json/wp/v2/pages?slug=banker-of-the-day'
response_page = scraper.get(wp_url, auth=HTTPBasicAuth(username, app_password))

if response_page.status_code != 200:
    print("Error fetching WordPress page:", response_page.status_code)
    exit()

page_data = response_page.json()
page_id = page_data[0]['id']
current_html = page_data[0]['content']['rendered']

soup_wp = BeautifulSoup(current_html, "html.parser")
wp_table = soup_wp.find("table", {"id": "free-tip"})

if not wp_table:
    print("Error: Table with id 'free-tip' not found in WordPress page.")
    exit()

# Insert new rows at the top of the table body
tbody = wp_table.find("tbody")
new_rows = BeautifulSoup(output_rows, "html.parser")

for new_row in reversed(new_rows.find_all("tr")):
    tbody.insert(0, new_row)

updated_html = str(soup_wp)

# ---------------- UPDATE WORDPRESS PAGE ----------------
update_url = f'https://grabfixedmatch.com/wp-json/wp/v2/pages/{page_id}'
response_update = requests.post(update_url, auth=HTTPBasicAuth(username, app_password), json={"content": updated_html})

if response_update.status_code == 200:
    print("WordPress page updated successfully ✅")
else:
    print("Error updating page:", response_update.status_code, response_update.text)
