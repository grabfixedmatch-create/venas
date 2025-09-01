import requests
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta
import random

username = "pettarr97@gmail.com"
app_password = "NOfC cNK5 M1le lvvY HfEZ FqhU"


today = datetime.now()
day_name = today.strftime("%A")
formatted_date = today.strftime("%A - %d/%m/%Y")

url = "https://bankerpredict.com/banker-of-the-day"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, "html.parser")

table = soup.find_all("table")

print(table)

# Extract all rows
# rows = table.find("tbody").find_all("tr")

# output_rows = ""
# for row in rows:
#     cols = row.find_all("td")
#     time = cols[0].get_text(strip=True)
#     league = cols[1].get_text(strip=True)
#     match = cols[2].get_text(" ", strip=True)
#     tip = cols[3].get_text(strip=True).capitalize()
    
#     search_url = f"https://www.google.com/search?q={match.replace(' ', '+')}+result"
#     output_rows += f"""
# <tr>
#     <td>{time}</td>
#     <td>{league}</td>
#     <td>{match}</td>
#     <td>{tip}</td>
#     <td><a href="{search_url}" target="_blank">Check</a></td>
# </tr>
# """

# # ---------------- FETCH WORDPRESS PAGE ----------------
# wp_url = 'https://grabfixedmatch.com/wp-json/wp/v2/pages?slug=banker-of-the-day'

# response_page = requests.get(wp_url, auth=HTTPBasicAuth(username, app_password))

# if response_page.status_code != 200:
#     print("Error fetching page:", response_page.status_code)
#     exit()

# page_data = response_page.json()
# page_id = page_data[0]['id']
# current_html = page_data[0]['content']['rendered']

# soup_wp = BeautifulSoup(current_html, "html.parser")

# wp_table = soup_wp.find("table", {"id": "free-tip"})

# if wp_table:
#     tbody = wp_table.find("tbody")
#     new_rows = BeautifulSoup(output_rows, "html.parser")

#     for new_row in reversed(new_rows.find_all("tr")):
#         tbody.insert(0, new_row)

#     updated_html = str(soup_wp)

#     update_url = f'https://grabfixedmatch.com/wp-json/wp/v2/pages/{page_id}'
#     data = {"content": updated_html}
#     response_update = requests.post(update_url, auth=HTTPBasicAuth(username, app_password), json=data)

#     if response_update.status_code == 200:
#         print("Page updated successfully ✅")
#     else:
#         print("Error updating page:", response_update.status_code, response_update.text)
# else:
#     print("Table with id 'free-tip' not found in page.")
