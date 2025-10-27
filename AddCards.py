import requests
import os
from dotenv import load_dotenv
import re

load_dotenv()
API_KEY = os.getenv("API_KEY")
TOKEN = os.getenv("TOKEN")
BOARD_ID = os.getenv("BOARD_ID")
LIST_NAME = "General BackLog"  # Change this to your target list name

def get_list_id(board_id, list_name):
    url = f"https://api.trello.com/1/boards/{board_id}/lists?key={API_KEY}&token={TOKEN}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch lists: {response.text}")
        return None
    lists = response.json()
    for lst in lists:
        if lst["name"] == list_name:
            return lst["id"]
    print(f"List '{list_name}' not found on board {board_id}.")
    return None

def add_cards_from_file(filename, board_id, list_name):
    list_id = get_list_id(board_id, list_name)
    if not list_id:
        print("Cannot proceed without a valid list ID.")
        return

    # Fetch all labels on the board
    def get_label_id(board_id, name, color):
        url = f"https://api.trello.com/1/boards/{board_id}/labels?key={API_KEY}&token={TOKEN}"
        resp = requests.get(url)
        if resp.status_code == 200:
            for label in resp.json():
                if label["name"] == name:
                    return label["id"]
        # If not found, create it
        create_url = f"https://api.trello.com/1/labels"
        params = {
            "key": API_KEY,
            "token": TOKEN,
            "idBoard": board_id,
            "name": name,
            "color": color
        }
        create_resp = requests.post(create_url, params=params)
        if create_resp.status_code == 200:
            return create_resp.json()["id"]
        else:
            print(f"Failed to create label: {create_resp.text}")
            return None

    current_heading = None
    heading_label_id = None
    with open(filename, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            # Check if line is a card or a heading
            match = re.match(r"^(.*)\((\d+)\s*hrs?\)$", line)
            if match:
                card_name = match.group(1).strip()
                label_value = match.group(2)
                # Create card
                url = f"https://api.trello.com/1/cards"
                params = {
                    "key": API_KEY,
                    "token": TOKEN,
                    "idList": list_id,
                    "name": card_name,
                }
                response = requests.post(url, params=params)
                if response.status_code == 200:
                    card = response.json()
                    card_id = card["id"]
                    print(f"Created card: {card_name}")

                    # Add hour label
                    if label_value:
                        if label_value == "1":
                            color = "green"
                        elif label_value == "2":
                            color = "yellow"
                        elif label_value == "4":
                            color = "orange"
                        else:
                            color = "red"
                        label_id = get_label_id(board_id, label_value, color)
                        print(f"Hour label id for value {label_value}: {label_id}")
                        if label_id:
                            add_label_url = f"https://api.trello.com/1/cards/{card_id}/idLabels"
                            add_label_params = {
                                "key": API_KEY,
                                "token": TOKEN,
                                "value": label_id
                            }
                            add_label_resp = requests.post(add_label_url, params=add_label_params)
                            print(f"Hour label response: {add_label_resp.status_code} {add_label_resp.text}")
                            if add_label_resp.status_code == 200:
                                print(f"Added label {label_value} to card {card_name}")
                            else:
                                print(f"Failed to add label: {add_label_resp.text}")
                    # Add heading label
                    print(f"Current heading: {current_heading}, heading_label_id: {heading_label_id}")
                    if heading_label_id:
                        add_label_url = f"https://api.trello.com/1/cards/{card_id}/idLabels"
                        add_label_params = {
                            "key": API_KEY,
                            "token": TOKEN,
                            "value": heading_label_id
                        }
                        add_label_resp = requests.post(add_label_url, params=add_label_params)
                        print(f"Heading label response: {add_label_resp.status_code} {add_label_resp.text}")
                        if add_label_resp.status_code == 200:
                            print(f"Added heading label '{current_heading}' to card {card_name}")
                        else:
                            print(f"Failed to add heading label: {add_label_resp.text}")
                else:
                    print(f"Failed to create card: {response.text}")
            else:
                # Treat as heading
                current_heading = line
                # Always create a new label for each heading
                create_url = f"https://api.trello.com/1/labels"
                params = {
                    "key": API_KEY,
                    "token": TOKEN,
                    "idBoard": board_id,
                    "name": current_heading,
                    "color": "blue"
                }
                create_resp = requests.post(create_url, params=params)
                if create_resp.status_code == 200:
                    heading_label_id = create_resp.json()["id"]
                    print(f"Created new heading label: {current_heading}, heading_label_id: {heading_label_id}")
                else:
                    heading_label_id = None
                    print(f"Failed to create heading label: {create_resp.text}")

# Usage example:
# add_cards_from_file("cards.txt", BOARD_ID, LIST_NAME)
add_cards_from_file("cards.txt", BOARD_ID, LIST_NAME)
