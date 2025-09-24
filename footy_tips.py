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
# username = os.environ.get("WP_USERNAME")
# app_password = os.environ.get("WP_APP_PASSWORD")

username = "pettarr97@gmail.com"
app_password = "Drzj RwZt kqgj pjgg Q6WT omhE"

# if not username or not app_password:
#     raise ValueError("WP_USERNAME and WP_APP_PASSWORD must be set in environment variables.")

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

# ---------------- FETCH WORDPRESS PAGE ----------------
wp_url = 'https://footy1x2.info/wp-json/wp/v2/posts/259'
response = scraper.get(wp_url, auth=HTTPBasicAuth(username, app_password))

if response.status_code == 200:
    post_data = response.json()
    current_content = post_data.get("content", {}).get("rendered", "")
    
    soup = BeautifulSoup(current_content, "html.parser")
    tbody = soup.find("tbody")

    if tbody:
        # Append new rows
        for row_html in reversed(formatted_rows):
            new_row = BeautifulSoup(row_html, "html.parser")
            tbody.insert(0, new_row)
        
        updated_content = str(soup)

        update_response = scraper.put(
            wp_url,
            auth=HTTPBasicAuth(username, app_password),
            json={"content": updated_content}
        )
        
        if update_response.status_code == 200:
            print("Post updated successfully!")
        else:
            print("Failed to update post:", update_response.status_code, update_response.text)
        
    else:
        print("No <tbody> found in the post content.")
else:
    print("Failed to fetch post:", response.status_code, response.text)

# page_data = response_page.json()
# page_id = page_data[0]['id']
# current_html = page_data[0]['content']['rendered']

# soup_wp = BeautifulSoup(current_html, "html.parser")
# wp_table = soup_wp.find("table", {"id": "free-tip"})

# if not wp_table:
#     print("Error: Table with id 'free-tip' not found in WordPress page.")
#     exit()

# # Insert new rows at the top of the table body
# tbody = wp_table.find("tbody")
# new_rows = BeautifulSoup(output_rows, "html.parser")

# for new_row in reversed(new_rows.find_all("tr")):
#     tbody.insert(0, new_row)

# updated_html = str(soup_wp)

# # # ---------------- UPDATE WORDPRESS PAGE ----------------
# update_url = f'https://grabfixedmatch.com/wp-json/wp/v2/pages/{page_id}'
# response_update = requests.post(update_url, auth=HTTPBasicAuth(username, app_password), json={"content": updated_html})

# if response_update.status_code == 200:
#     print("WordPress page updated successfully ✅")
# else:
#     print("Error updating page:", response_update.status_code, response_update.text)