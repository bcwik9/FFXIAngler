import cv2 as cv
import numpy as np
import time
from datetime import datetime
from windowcapture import WindowCapture
import keyboard
import functools
import random
import win32gui
import yaml


# Notes on usage #
# Macros required: Ctrl + 1 = '/fishing'
# As the bot reads the chat log to release monsters/items Ashita Logs plugin is necessary: https://docsv3.ashitaxi.com/addons/logs
# I have tested this on private servers using 1280 * 720 windowed mode and it works without error until bait is completely used
# Found it best to point the screen down at the feet of the char to minimise changing scenery in the background which may confuse the bot

### TODO MESSAGES
# You can't fish without bait on the hook.
# <PLAYERNAME> caught a crayfish!
# You give up and reel in your line.
# You don't know how much longer you can keep this one on the line...
# You cannot fish here.
# You didn't catch anything.
# <PLAYERNAME> caught a crayfish, but cannot carry any more items.

# Load settings from settings.yml
with open('settings.yml', 'r') as file:
    settings = yaml.safe_load(file)

### Config ###
# Change this to the title of your FFXI window, normally it is Character name
ffxi_window_name = settings.get('ffxi_window_name')
# This should be the path to your chatlogs from the Logs addon
path_str = settings.get('chat_log_path')
path = rf"{path_str}"
# Screen width
screen_width = settings.get('screen_width')
# Allow fishing of itmes
allow_items = True
# Allow fishing of monsters
allow_monsters = False


# initialize the WindowCapture class
wincap = WindowCapture(ffxi_window_name)
# Target Images
gold_img = cv.imread('./pics/gold.png', cv.IMREAD_UNCHANGED)
silver_img = cv.imread('./pics/silver.png', cv.IMREAD_UNCHANGED)

# Set initial values
state = {
    'fishing': False,
    'fish_on_line': False,
    'allow_monsters': settings.get('allow_monsters', True) == True,
    'allow_items': settings.get('allow_items', False) == True,
    'last_message_read': None,
    'last_arrow_found_at': None,
    # Lower this value if you get lots of false positives
    # Raise this value if you get no matches
    'threshold': 0.017
}
fish_caught = 0
month = datetime.now().month
file_name = f'\\{ffxi_window_name}_{datetime.now().year}.{datetime.now().month:02d}.{datetime.now().day:02d}.log'
# Get the handle of the FFXI window
hwnd = win32gui.FindWindow(None, ffxi_window_name)
if hwnd == 0:
    raise Exception(f"Window with title '{ffxi_window_name}' not found")

# Skip monsters, items, and other stuff by reading logs
def handle_logs():
    logs = open(path + file_name, 'rb')
    log_lines = [line.decode('utf-8', errors='ignore') for line in logs.readlines()[-10::]]

    # Filter to only new messages
    new_messages = []
    last_line_found = False
    for line in log_lines:
        if not state['last_message_read']:
            new_messages.append(line)
            continue

        if state['last_message_read'] == line:
            last_line_found = True
            continue

        if last_line_found:
            new_messages.append(line)

    state['last_message_read'] = log_lines[-1]

    # Return if there's nothing new
    if not new_messages:
        logs.close()
        return

    searchable_new_messages = b''.join([line.encode('utf-8') for line in new_messages])
    monster = b'ferociously!'
    monster_check = monster in searchable_new_messages
    item = b'pulling'
    item_check = item in searchable_new_messages
    terrible = b'terrible'
    terrible_check = terrible in searchable_new_messages
    no_catch = b'You didn\'t catch anything.'
    no_catch_check = no_catch in searchable_new_messages
    lost_catch = b'You lost your catch.'
    lost_catch_check = lost_catch in searchable_new_messages
    gave_up = b'You give up.'
    gave_up_check = gave_up in searchable_new_messages
    
    if (monster_check and not state['allow_monsters']) or (item_check and not state['allow_items']) or terrible_check or no_catch_check or lost_catch_check or gave_up_check:
        if no_catch_check:
            print('No catch')
        elif lost_catch_check:
            print('Lost catch')
        elif terrible_check:
            print('Terrible feeling, reeling in')
        elif gave_up_check:
            print('Gave up')
        else:
            print('Monster or item, reeling in')
        focus_window()
        time.sleep(1.2)
        send_keypress("esc")
        state['fishing'] = False
        state['fish_on_line'] = False
        logs.close()
        return

    fish_on_line = b'Something caught the hook!'
    fish_on_line_check = fish_on_line in searchable_new_messages or terrible_check or item_check
    if fish_on_line_check:
        print('Fish on line')
        state['fish_on_line'] = True
        state['fishing'] = False
        state['last_arrow_found_at'] = time.time()
        logs.close()
        return

    no_bait = b'You can\'t fish without bait on the hook.'
    no_bait_check = no_bait in searchable_new_messages
    if no_bait_check:
        print('No bait, tryint to equip more with CTRL+2')
        focus_window()
        send_keypress('esc')
        time.sleep(0.5)
        send_keypress('ctrl+2')
        state['fishing'] = False
        state['fish_on_line'] = False
        logs.close()
        return

def cast():
    if not state['fishing']:
        print("Casting with CTRL+1")
        focus_window()
        send_keypress('esc')
        time.sleep(6)
        send_keypress('ctrl+1')
        state['fishing'] = True
        state['fish_on_line'] = False
        #calibrate_sensitivity()

def send_keypress(key):
    keyboard.press_and_release(key)

def focus_window():
    #print("Focusing window")
    # Bring the target window to the foreground
    win32gui.SetForegroundWindow(hwnd)
    # Wait before sending any commands
    time.sleep(0.75)

def check_for_fish_arrows():
    # get an updated image of the game
    screenshot = wincap.get_screenshot()

    # Check for matches
    result_gold = cv.matchTemplate(screenshot, gold_img, cv.TM_SQDIFF_NORMED)
    result_silver = cv.matchTemplate(screenshot, silver_img, cv.TM_SQDIFF_NORMED)

    # Get any matches
    locations_gold = np.where(result_gold <= state['threshold'])
    locations_silver = np.where(result_silver <= state['threshold'])
    locations_gold = list(zip(*locations_gold[::-1]))
    locations_silver = list(zip(*locations_silver[::-1]))

    # get the x value on all locations
    loc = []
    if locations_gold:
        loc = locations_gold[0]
    elif locations_silver:
        loc = locations_silver[0]

    return loc
    

def calibrate_sensitivity():
    calibrating = True
    #send_keypress('esc')
    #time.sleep(0.5)
    #send_keypress('esc')
    #time.sleep(0.5)
    #send_keypress('f')
    # This value determines if the match is good enough or not, range from 0.00 ~ 0.99
    # The lower the value the closer the match needs to be
    # Lower this value if you get lots of false positives
    # Raise this value if you get no matches
    state['threshold'] = 0.25
    num_passed = 0
    
    while calibrating:
        print(f"Calibrating threshold: {state['threshold']}")
        loc = check_for_fish_arrows()
        if loc:
            num_passed = 0
            # lower threshold
            state['threshold'] -= 0.001
        else:
            num_passed += 1
            if num_passed >= 5:
                calibrating = False
                # add buffer to threshold to be safe
                #state['threshold'] += 0.001

    send_keypress('esc')


### START ###
# look at the window
focus_window()

# calibrate screen sensitivity
calibrate_sensitivity()
print(f"Calibrated threshold: {state['threshold']}")
while(False):
    print(f"{check_for_fish_arrows()}")

#exit()

# set up logs
print("*** Setting up logs, ignore the following messages ****")
handle_logs()
print("*** Finished setting up logs ****")

# reset vars
state['fishing'] = False
state['fish_on_line'] = False

# Main loop
while(True):
    if not state['fishing'] and not state['fish_on_line']:
        cast()

    # Check logs if we're fishing for messages
    if state['fishing'] and not state['fish_on_line']:
        handle_logs()

    loc = check_for_fish_arrows()
    #print(f"LOC: {loc == []} ({loc})")
    if loc:
        #print("FISH ARROW FOUND")

        if state['fish_on_line']:
            # Make sure arrows marked as detected
            state['last_arrow_found_at'] = time.time()

            screen_width_half = (screen_width / 2)
            # Check if right or left then log and press key
            if loc[0] > screen_width_half:
                print("Right arrow found")
                send_keypress("d")
                time.sleep(1)
            else:
                print('Left arrow found')
                send_keypress("a")
                time.sleep(1)

    # If we are fishing and there are no more arrows then it is safe to assume the fish is out of stam and we can reel it in
    if state['fish_on_line'] and (time.time() - state['last_arrow_found_at']) >= 3:
        print("Caught Fish")
        fish_caught += 1
        print(f"Fished: {fish_caught} fish")
        random_wait = random.choice([0.1, 0.2, 0.3, 0.4, 0.5])
        time.sleep(random_wait)
        send_keypress("enter")
        state['fish_on_line'] = False
        state['fishing'] = False
        time.sleep(2)