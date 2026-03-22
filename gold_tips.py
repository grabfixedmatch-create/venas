import cloudscraper
from bs4 import BeautifulSoup
import xmlrpc.client

# ---------------- CONFIG ----------------
WP_XMLRPC = "https://goldfixedmatches.com/xmlrpc.php"
USERNAME = "admin"
PASSWORD = "ot23 QCqi HfMW nACD 8SLV SoQK"
POST_ID = 207

SCRAPE_URL = "https://eaglepredict.com/predictions/bet-of-the-day/"

# ---------------- SCRAPE ----------------
scraper = cloudscraper.create_scraper()
html = scraper.get(SCRAPE_URL).text

soup = BeautifulSoup(html, "html.parser")
sections = soup.find_all("div", class_="row-start-1 col-start-1")

rows_html = ""

for section in sections:
    try:
        # -------- LEAGUE --------
        league_block = section.select_one(".flex.items-center.gap-2")
        league = league_block.find("span").text.strip()
        league_logo = league_block.find("img")["src"]

        # -------- TIME & DATE --------
        time_ = section.select(".flex.items-center.gap-2 p")[0].text.strip()
        date_ = section.select(".flex.items-center.gap-2 p")[1].text.strip()

        # -------- TEAMS --------
        teams = section.select("div.grid-cols-4 div")

        home = teams[0].p.text.strip()
        home_logo = teams[0].img["src"]

        away = teams[2].p.text.strip()
        away_logo = teams[2].img["src"]

        # -------- TIP --------
        prediction = section.select_one("div.bg-base-300").text.strip()

        # -------- ROW --------
        row = f"""
<tr>
    <td>
        <span style="display:block;">{date_}</span>
        <span style="display:block; font-size:12px; opacity:0.8;">{time_}</span>
    </td>

    <td>
        <span style="display:inline-flex; align-items:center; margin-right:6px;">
            <img src="{home_logo}" width="18" style="margin-right:4px;">
            {home}
        </span>

        <span style="margin: 0 6px;">vs</span>

        <span style="display:inline-flex; align-items:center; margin-left:6px;">
            <img src="{away_logo}" width="18" style="margin-right:4px;">
            {away}
        </span>
    </td>

    <td></td>

    <td><strong>{prediction}</strong></td>

    <td>
        <img src="{league_logo}" width="20" title="{league}">
    </td>
</tr>
"""
        rows_html += row

        # ---- LIMIT TO 1 MATCH ----
        break

    except Exception as e:
        print("Skipping section:", e)

# ---------------- XML-RPC CONNECT ----------------
client = xmlrpc.client.ServerProxy(WP_XMLRPC)

# ---------------- GET POST ----------------
post = client.wp.getPost(0, USERNAME, PASSWORD, POST_ID)

content = post["post_content"]

soup = BeautifulSoup(content, "html.parser")

table = soup.find("table", id="soccer-predictions-table")
if not table:
    raise Exception("Table not found")

tbody = table.find("tbody")
if not tbody:
    raise Exception("No tbody found")

# -------- INSERT NEW ROWS (APPEND, KEEP OLD ROWS) --------
new_rows = BeautifulSoup(rows_html, "html.parser").find_all("tr")
for r in new_rows:
    tbody.append(r)

updated_content = str(soup)

# ---------------- UPDATE POST ----------------
client.wp.editPost(
    0,
    USERNAME,
    PASSWORD,
    POST_ID,
    {
        "post_content": updated_content
    }
)

print("✅ Post updated successfully via XML-RPC!")
