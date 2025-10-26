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
cardsLeftToDo = 0
startDate = None
graphMap = {}
def CollectData():
    global cardsLeftToDo
    global startDate
    #test
    allowedLists = ["Sprint 1 Backlog", "Tyler", "Vincent", "Connor", "Avi", "Ethan"]
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
        # print(lst["name"] + "is in allowed lists is " +  (lst["name"] in allowedLists).__str__())
        if(lst["name"] in allowedLists):
            accepted_Lists.append(lst)
            # print(lst["name"], " List ID:", accepted_Lists[-1]["id"])
            LIST_ID = lst["id"]
            url = f"https://api.trello.com/1/lists/{LIST_ID}/cards?key={API_KEY}&token={TOKEN}"
            response = requests.get(url)
            cards_List = response.json()
            for cards in cards_List:
                label_sum = 0
                for label in cards.get("labels", []):
                    # Try to parse label name as a number
                    try:
                        label_sum += float(label["name"])
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



def ShowDataGraph():
    import matplotlib.pyplot as plt

    dates = []
    cardsLeft = []

    for dateStr in sorted(graphMap.keys()):
        try:
            dates.append(datetime.strptime(dateStr, '%Y-%m-%d'))
            cardsLeft.append(graphMap[dateStr])
        except ValueError:
            print(f"Skipping invalid date: {dateStr}")

    plt.figure(figsize=(10, 5))
    plt.plot(dates, cardsLeft, marker='o')
    plt.xlabel('Date')
    plt.ylabel('Cards Left to Do')
    plt.title('Burn Down Chart')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.ylim(0, max(cardsLeft) + 2)
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

