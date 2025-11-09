import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import sys

load_dotenv()
API_KEY = os.getenv("API_KEY")
TOKEN = os.getenv("TOKEN")
BOARD_ID = os.getenv("BOARD_ID")

# Defaults
SPRINT_FILE = "Sprint1 BurnDownChart"  # fallback if Print1 not present
OUTPUT_FILE = "ProductInfo.txt"


def get_board_label_sum(board_id):
    """Fetch all cards on the board and sum integer label names."""
    url = f"https://api.trello.com/1/boards/{board_id}/cards?key={API_KEY}&token={TOKEN}&fields=name,labels"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch board cards: {resp.status_code} {resp.text}")
    cards = resp.json()
    total = 0
    for card in cards:
        for label in card.get("labels", []):
            name = label.get("name", "").strip()
            try:
                total += int(name)
            except ValueError:
                # not an int label, ignore
                continue
    return total


def read_sprint_file(path):
    """Read sprint file and return list of (dateStr, intVal) and startDate if present."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sprint file not found: {path}")
    lines = []
    start_date = None
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if parts[0] == "StartDate":
                if len(parts) > 1:
                    start_date = parts[1]
            else:
                try:
                    val = float(parts[1]) if "." in parts[1] else int(parts[1])
                except Exception:
                    # fallback to 0
                    val = 0
                lines.append((parts[0], val))
    return lines, start_date


def write_product_file(path, entries, start_date=None):
    with open(path, "w") as f:
        for dateStr, val in entries:
            # Write integer if whole number, otherwise keep decimal
            if isinstance(val, float) and val.is_integer():
                val_out = int(val)
            else:
                val_out = val
            f.write(f"{dateStr},{val_out}\n")
        if start_date is not None:
            f.write(f"StartDate,{start_date}\n")


if __name__ == "__main__":
    # choose sprint file: prefer Print1 BurnDownChart.txt if present
    preferred = "Print1 BurnDownChart.txt"
    sprint_path = preferred if os.path.exists(preferred) else SPRINT_FILE

    try:
        product_sum = get_board_label_sum(BOARD_ID)
        print(f"Product total (sum of int labels on board): {product_sum}")
    except Exception as e:
        print("Error fetching board labels:", e)
        raise

    try:
        sprint_entries, start_date = read_sprint_file(sprint_path)
    except Exception as e:
        print("Error reading sprint file:", e)
        raise

    # Build product backlog over time:
    # Start = product_sum + sprint_start (so day 1 shows the sum of both)
    # Then each day subtract how many the sprint burndown decreased since previous day
    product_entries = []
    if not sprint_entries:
        print("No sprint entries found; nothing to write")
        write_product_file(OUTPUT_FILE, product_entries, start_date)
        print(f"Wrote {len(product_entries)} lines to {OUTPUT_FILE}")
        raise SystemExit(0)

    # Ensure sprint_entries are in chronological order (they should be)
    dates = [d for d, v in sprint_entries]
    values = [v for d, v in sprint_entries]

    sprint_start = values[0]
    product_current = product_sum + sprint_start
    # Day 0 / first date
    product_entries.append((dates[0], product_current))

    # For each subsequent day, subtract the sprint drop (previous - current)
    for i in range(1, len(values)):
        prev = values[i-1]
        curr = values[i]
        delta = prev - curr  # how many completed in sprint between days
        product_current = product_current - delta
        product_entries.append((dates[i], product_current))

    write_product_file(OUTPUT_FILE, product_entries, start_date)
    print(f"Wrote {len(product_entries)} lines to {OUTPUT_FILE}")
    # If user requested graphing, plot the product backlog with recommended line
    if len(sys.argv) > 1 and sys.argv[1] in ("-graph", "--graph"):
        try:
            import matplotlib.pyplot as plt

            # prepare dates and values
            dates = [datetime.strptime(d, "%Y-%m-%d") for d, v in product_entries]
            values = [v for d, v in product_entries]

            plt.figure(figsize=(10, 5))
            plt.plot(dates, values, marker='o', label='Product Backlog')

            # recommended line target: Dec 9 of the same year as first data point
            if dates:
                year = dates[0].year
                target_date = datetime(year, 12, 9)
                # if target_date is before first date, push to next year
                if target_date <= dates[0]:
                    target_date = datetime(year + 1, 12, 9)
                start_val = values[0]
                plt.plot([dates[0], target_date], [start_val, 0], linestyle='--', color='red', label='Recommended')
                # extend x-axis to include target
                all_dates = dates + [target_date]
            else:
                all_dates = dates

            plt.xlabel('Date')
            plt.ylabel('Product Backlog')
            plt.title('Product Backlog Burn Down')
            plt.grid(True)
            plt.xticks(rotation=45)
            if values:
                plt.ylim(0, max(values) + 2)
            plt.legend()
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print('Failed to plot graph:', e)
