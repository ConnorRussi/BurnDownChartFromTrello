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

def UpdateProductInfoFromLongTerm():
    """
    Updates ProductInfo.txt based on total sprint changes in Long Term.txt
    Formula: new_product_value = original_product_value - (sprint_start_value - current_sprint_value)
    """
    try:
        # Read Long Term.txt data
        lt_entries, lt_start = _read_sprint_file("Long Term.txt")
        if not lt_entries or not lt_start:
            print("No data in Long Term.txt or no start date found")
            return

        # Read existing ProductInfo.txt
        prod_entries, prod_start = _read_sprint_file(productData + ".txt")
        
        # Convert to dictionaries for easier lookup
        lt_dict = {date_str: value for date_str, value in lt_entries}
        prod_dict = {date_str: value for date_str, value in prod_entries}
        
        print(f"Long Term start date: {lt_start}")
        print(f"Product Info start date: {prod_start}")
        
        # Get the sprint start value from Long Term.txt
        if lt_start not in lt_dict:
            print(f"Start date {lt_start} not found in Long Term data")
            return
        
        sprint_start_value = lt_dict[lt_start]
        print(f"Sprint start value: {sprint_start_value}")
        
        # Get the original product value for the start date
        if lt_start not in prod_dict:
            print(f"Start date {lt_start} not found in Product Info")
            return
        
        original_product_value = prod_dict[lt_start]
        print(f"Original product value at start: {original_product_value}")
        
        # Process each date in Long Term.txt
        for date_str, current_sprint_value in lt_entries:
            if date_str in prod_dict:
                # Calculate new product value using the formula:
                # new_product_value = original_product_value - (sprint_start_value - current_sprint_value)
                sprint_change = sprint_start_value - current_sprint_value
                new_product_value = original_product_value - sprint_change
                
                old_value = prod_dict[date_str]
                prod_dict[date_str] = new_product_value
                
                print(f"Updated {date_str}: {old_value} -> {new_product_value}")
                print(f"  Sprint: {sprint_start_value} -> {current_sprint_value} (change: {sprint_change})")
                
            else:
                # Handle missing dates - use previous product value and apply the same logic
                prev_product_value = _get_previous_product_value(prod_dict, date_str)
                if prev_product_value == 0:
                    # If no previous value found, use the original start value
                    prev_product_value = original_product_value
                
                sprint_change = sprint_start_value - current_sprint_value
                new_product_value = original_product_value - sprint_change
                
                prod_dict[date_str] = new_product_value
                print(f"Added {date_str}: {new_product_value} (based on start: {original_product_value})")
                print(f"  Sprint: {sprint_start_value} -> {current_sprint_value} (change: {sprint_change})")
        
        # Convert back to list of tuples and sort by date
        updated_entries = [(date_str, value) for date_str, value in prod_dict.items()]
        updated_entries.sort(key=lambda x: x[0])
        
        # Write updated data back to file
        _write_product_file(productData + ".txt", updated_entries, prod_start)
        print("ProductInfo.txt updated successfully based on Long Term.txt sprint changes")
        
    except Exception as e:
        print(f"Error updating ProductInfo from Long Term: {e}")


def _get_previous_product_value(prod_dict, target_date):
    """
    Get the value from the previous available date in ProductInfo
    """
    # Convert target date to datetime for comparison
    from datetime import datetime
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    
    # Find the closest previous date
    prev_value = 0  # Default if no previous date found
    prev_dt = None
    
    for date_str, value in prod_dict.items():
        try:
            date_dt = datetime.strptime(date_str, "%Y-%m-%d")
            if date_dt < target_dt:
                if prev_dt is None or date_dt > prev_dt:
                    prev_dt = date_dt
                    prev_value = value
        except ValueError:
            continue
    
    return prev_value


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

# Always update product info based on Long Term.txt after collecting data
UpdateProductInfoFromLongTerm()

if len(sys.argv) > 1 and sys.argv.__contains__("-graph"):
    ShowDataGraph()

if len(sys.argv) > 1 and ("-product" in sys.argv or "-product-graph" in sys.argv):
    ShowProductGraph()

if len(sys.argv) > 1 and ("-update-product" in sys.argv or "-update" in sys.argv):
    UpdateProductInfoFromLongTerm()





