import cv2 as cv
import numpy as np
import time
from datetime import datetime
from windowcapture import WindowCapture
import keyboard
import functools
import random

# Notes on usage #
# I am not a Python dev so this might be inefficient and ugly... but it works
# Macros required: Ctrl + 1 = '/fishing'
# As the bot reads the chat log to release monsters/items Ashita Logs plugin is necessary: https://docsv3.ashitaxi.com/addons/logs
# Again as the bot looks at the last 2 lines of the log try to minimise log spam (filter chat) and unequip linkshell is recommended
# I have tested this on private servers using 1280 * 720 windowed mode and it works without error until bait is completely used
# I have only tested this at the Knightwell fishing for moat carp, other areas most likely work but haven't been tested and may need differing thresholds
# Found it best to point the screen down at the feet of the char to minimise changing scenery in the background which may confuse the bot
# Any improvements / feedback welcome, looking to add bait re-equipping in the future

# Change this to the title of your FFXI window, normally it is Character name
ffxi_window_name = 'REPLACE ME'
# initialize the WindowCapture class
wincap = WindowCapture(ffxi_window_name)
# Target Images
gold_img = cv.imread('./pics/gold.png', cv.IMREAD_UNCHANGED)
silver_img = cv.imread('./pics/silver.png', cv.IMREAD_UNCHANGED)
# Set initial values
fishing = False
last_results = []
start_time = time.time()
fish_caught = 0
month = datetime.now().month
file_name = f'\\{ffxi_window_name}_{datetime.now().year}.{datetime.now().month:02d}.{datetime.now().day:02d}.log'
# This should be the path to your chatlogs from the Logs addon
path = r"C:<REPLACE THIS PATH>\Ashita\chatlogs"

# Skip monsters and items by reading logs
def handle_logs():
    logs = open(path + file_name, 'rb')
    last_messages = b''.join(logs.readlines()[-2::])
    monster = b'ferociously!'
    item = b'pulling'
    if monster in last_messages or item in last_messages:
        print('Letting go monster/item')
        keyboard.press_and_release("esc")
        time.sleep(30)
        keyboard.press_and_release('ctrl+1')
        global start_time
        start_time = time.time()
        logs.close
        return False

# Main loop
while(True):
    # Failsafe to retry fishing again if nothing happens e.g. ('You give up')
    if (time.time() - start_time >= 35) and fishing == False:
        keyboard.press_and_release('ctrl+1')
        start_time = time.time()

    # get an updated image of the game
    screenshot = wincap.get_screenshot()

    # Check for matches
    result_gold = cv.matchTemplate(screenshot, gold_img, cv.TM_SQDIFF_NORMED)
    result_silver = cv.matchTemplate(screenshot, silver_img, cv.TM_SQDIFF_NORMED)

    # This value determines if the match is good enough or not, range from 0.00 ~ 0.99
    # The lower the value the closer the match needs to be
    # Lower this value if you get lots of false positives
    # Raise this value if you get no matches
    threshold = 0.475

    # Get any matches
    locations_gold = np.where(result_gold <= threshold)
    locations_silver = np.where(result_silver <= threshold)
    locations_gold = list(zip(*locations_gold[::-1]))
    locations_silver = list(zip(*locations_silver[::-1]))

    # get the x value on all locations
    loc = []
    if locations_gold:
        loc = locations_gold[0]
    elif locations_silver:
        loc = locations_silver[0]

    if loc:
        result = True
        # Initial check of logs to see if we just release
        if fishing == False:
            result = handle_logs()
        if result == False:
            fishing = False
        else:
            fishing = True
        # Record succesful match
        last_results.append(1)

        # Replace the 1280 with your screen width. e.g. for 1920 * 1080 choose 1920
        screen_width_half = (1280 / 2)
        if fishing:
            # Check if right or left then log and press key
            if loc[0] > screen_width_half:
                print("Right")
                keyboard.press_and_release("d")
                time.sleep(1)
            else:
                print('Left')
                keyboard.press_and_release("a")
                time.sleep(1)
    else:
        # No location means no marker so add negative result
        last_results.append(0)

    # If we are fishing and there are no more arrows then it is safe to assume the fish is out of stam and we can reel it in
    if fishing and (functools.reduce(lambda a, b: a+b, last_results[-5:]) == 0):
        print("Dead Fish")
        fish_caught += 1
        print(f"Fished: {fish_caught} fish")
        random_wait = random.choice([0.1, 0.2, 0.3, 0.4, 0.5])
        time.sleep(random_wait)
        keyboard.press_and_release("enter")
        fishing = False
        time.sleep(30)
        keyboard.press_and_release('ctrl+1')
        start_time = time.time()
