import requests
import json
from datetime import datetime, timedelta
import sys
import os
from dotenv import load_dotenv

# Load secrets from .env file (create .env with API_KEY, TOKEN, BOARD_ID)
load_dotenv()
API_KEY = os.getenv("API_KEY")
TOKEN = os.getenv("TOKEN")
BOARD_ID = os.getenv("BOARD_ID")
BOARD_LONGID = ""

fileName = "Long Term"
productData = "ProductInfo"
cardsLeftToDo = 0
startDate = None
graphMap = {}

def _fetch_product_label_sum(board_id):
    """Sum integer label names for all cards excluding finished lists."""
    try:
        # get lists to determine finished lists
        url = f"https://api.trello.com/1/boards/{board_id}/lists?key={API_KEY}&token={TOKEN}"
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Failed to fetch lists for product sum: {resp.status_code} {resp.text}")
            return None
        lists = resp.json()
        finished_list_ids = set()
        for lst in lists:
            name = lst.get("name", "").lower()
            if any(k in name for k in ("finish", "done", "complete")):
                finished_list_ids.add(lst.get("id"))

        total = 0
        # iterate lists and sum labels for cards not in finished lists
        for lst in lists:
            lid = lst.get("id")
            if lid in finished_list_ids:
                continue
            url_cards = f"https://api.trello.com/1/lists/{lid}/cards?key={API_KEY}&token={TOKEN}&fields=labels"
            r = requests.get(url_cards)
            if r.status_code != 200:
                print(f"Failed to fetch cards for list {lid}: {r.status_code} {r.text}")
                continue
            for card in r.json():
                for label in card.get("labels", []):
                    name = label.get("name", "").strip()
                    try:
                        total += int(name)
                    except ValueError:
                        continue
        return total
    except Exception as e:
        print("Error computing product label sum:", e)
        return None


def _read_sprint_file(path):
    entries = []
    start = None
    if not os.path.exists(path):
        return entries, start
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if parts[0] == "StartDate":
                if len(parts) > 1:
                    start = parts[1]
            else:
                try:
                    val = float(parts[1]) if "." in parts[1] else int(parts[1])
                except Exception:
                    val = 0
                entries.append((parts[0], val))
    return entries, start


def _write_product_file(path, entries, start_date=None):
    with open(path, "w") as f:
        for dateStr, val in entries:
            if isinstance(val, float) and val.is_integer():
                val_out = int(val)
            else:
                val_out = val
            f.write(f"{dateStr},{val_out}\n")
        if start_date is not None:
            f.write(f"StartDate,{start_date}\n")
def CollectData():
    global cardsLeftToDo
    global startDate
    #test
    # Only count lists whose name starts with 'sp '
    url = f"https://api.trello.com/1/boards/{BOARD_ID}/lists?key={API_KEY}&token={TOKEN}"
    response = requests.get(url)
    # print("Status code:", response.status_code)
    # print("Raw response:", response.text)
    if response.status_code != 200:
        # data = response.json()
        # print(data)
        print("Request failed. Check your URL, params, and credentials.")
    lists = response.json()
    accepted_Lists = []
    for lst in lists:
        # Check if list name starts with 'sp ' (case-insensitive)
        if lst["name"].lower().startswith("sp "):
            accepted_Lists.append(lst)
            LIST_ID = lst["id"]
            url = f"https://api.trello.com/1/lists/{LIST_ID}/cards?key={API_KEY}&token={TOKEN}"
            response = requests.get(url)
            cards_List = response.json()
            for cards in cards_List:
                label_sum = 0
                for label in cards.get("labels", []):
                    try:
                        label_sum += int(label["name"])
                    except (ValueError, KeyError):
                        continue
                cardsLeftToDo += label_sum
    #             print(cards["name"], cards["id"])
    #         print("*****************")
    # print("Total Cards Left To Do:", cardsLeftToDo)
    if(startDate is None):
        startDate = datetime.now()
    currentDate = datetime.now()
    graphMap[currentDate.strftime("%Y-%m-%d")] = cardsLeftToDo

    # Also update product backlog file: compute product sum and build product series
    try:
        product_sum = _fetch_product_label_sum(BOARD_ID)
        if product_sum is None:
            print("Skipping product update due to fetch error.")
            return

        # choose sprint file: prefer Print1 BurnDownChart.txt if present else Sprint1 BurnDownChart
        preferred = "Print1 BurnDownChart.txt"
        sprint_path = preferred if os.path.exists(preferred) else "Sprint1 BurnDownChart"
        sprint_entries, sprint_start = _read_sprint_file(sprint_path)

        if not sprint_entries:
            print("No sprint entries found; skipping product file update.")
            return

        # Build product backlog over time: start = product_sum + sprint_start, then subtract sprint daily deltas
        dates = [d for d, v in sprint_entries]
        values = [v for d, v in sprint_entries]
        sprint_start_val = values[0]
        product_current = product_sum + sprint_start_val
        product_entries = []
        product_entries.append((dates[0], product_current))
        for i in range(1, len(values)):
            prev = values[i-1]
            curr = values[i]
            delta = prev - curr
            product_current = product_current - delta
            product_entries.append((dates[i], product_current))
        # extend product entries up to today if needed (fill missing days with current value)
        try:
            last_date = datetime.strptime(product_entries[-1][0], '%Y-%m-%d').date()
            today = datetime.now().date()
            next_day = last_date + timedelta(days=1)
            while next_day <= today:
                product_entries.append((next_day.strftime('%Y-%m-%d'), product_current))
                next_day = next_day + timedelta(days=1)
        except Exception:
            pass

        _write_product_file(productData + ".txt", product_entries, sprint_start)
        print(f"Updated {productData}.txt with {len(product_entries)} entries")
    except Exception as e:
        print("Error updating product backlog:", e)



def SaveDataToFile():
    global startDate
    global graphMap
    with open(fileName + ".txt", "w") as f: 
        for dateStr, cardsLeft in graphMap.items():
            f.write(f"{dateStr},{cardsLeft}\n")
        if(startDate is not None):
            f.write(f"StartDate,{startDate.strftime('%Y-%m-%d')}\n")
        f.close()
    


def LoadDataFromFile():
    with open(fileName + ".txt", "r") as f:
        lines = f.readlines()
        for line in lines:
            parts = line.strip().split(',')
            if parts[0] == "StartDate":
                global startDate
                startDate = datetime.strptime(parts[1], '%Y-%m-%d')
            else:
                dateStr = parts[0]
                cardsLeft = int(parts[1])
                graphMap[dateStr] = cardsLeft
        f.close()
    # for dateStr, cardsLeft in graphMap.items():
    #     print(f"Date: {dateStr}, Cards Left: {cardsLeft}")
    # print("Start Date:", startDate.strftime('%Y-%m-%d'))



def ShowDataGraph(end_date=None):
    import matplotlib.pyplot as plt

    dates = []
    cardsLeft = []

    for dateStr in sorted(graphMap.keys()):
        try:
            dates.append(datetime.strptime(dateStr, '%Y-%m-%d'))
            cardsLeft.append(graphMap[dateStr])
        except ValueError:
            print(f"Skipping invalid date: {dateStr}")

    if not dates:
        print('No data to plot')
        return

    # Recommended line: true straight line from first day (start value) to a fixed end date
    plt.figure(figsize=(10, 5))
    plt.plot(dates, cardsLeft, marker='o', label='Actual')
    if len(dates) > 1:
        total_items = cardsLeft[0]
        # fixed recommended target date
        end_date = datetime(2025, 11, 21)
        # draw recommended line to end_date:
        plt.plot([dates[0], end_date], [total_items, 0], linestyle='--', color='red', label='Recommended')
        try:
            plt.xlim(dates[0], end_date)
        except Exception:
            pass

    plt.xlabel('Date')
    plt.ylabel('Cards Left to Do')
    plt.title('Burn Down Chart')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.ylim(0, max(cardsLeft) + 2)
    plt.legend()
    plt.tight_layout()
    plt.show()


def ShowProductGraph():
    import matplotlib.pyplot as plt
    prod_file = productData + ".txt"
    if not os.path.exists(prod_file):
        print(f"Product file not found: {prod_file}")
        return
    dates = []
    vals = []
    with open(prod_file, 'r') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split(',')
            if parts[0] == 'StartDate':
                continue
            try:
                dates.append(datetime.strptime(parts[0], '%Y-%m-%d'))
                if '.' in parts[1]:
                    vals.append(float(parts[1]))
                else:
                    vals.append(int(parts[1]))
            except Exception as e:
                print(f"Skipping invalid product line: {line} ({e})")
    if not dates:
        print('No product data to plot')
        return
    plt.figure(figsize=(10,5))
    plt.plot(dates, vals, marker='o', label='Product Backlog')
    # recommended straight line target Dec 9
    year = dates[0].year
    target_date = datetime(year, 12, 9)
    if target_date <= dates[0]:
        target_date = datetime(year+1, 12, 9)
    start_val = vals[0]
    plt.plot([dates[0], target_date], [start_val, 0], linestyle='--', color='red', label='Recommended')
    plt.xlabel('Date')
    plt.ylabel('Product Backlog')
    plt.title('Product Backlog')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.ylim(0, max(vals) + 2)
    plt.legend()
    plt.tight_layout()
    plt.show()

def ClearData():
    confirmation = input("Are you sure you want to clear all data? Type 'YES' (Case Sensitive) to confirm: ")
    if confirmation != 'YES':
        print("Clear data operation cancelled.")
        return -1
    global graphMap
    graphMap = {}
    startDate = datetime.now()
    SaveDataToFile()
    return 0


if len(sys.argv) > 1 and sys.argv.__contains__("-clear"):
    if(ClearData() == 0):
        print("Data cleared.")
        sys.exit()

LoadDataFromFile()
CollectData()
SaveDataToFile()

if len(sys.argv) > 1 and sys.argv.__contains__("-graph"):
    ShowDataGraph()

if len(sys.argv) > 1 and ("-product" in sys.argv or "-product-graph" in sys.argv):
    ShowProductGraph()





