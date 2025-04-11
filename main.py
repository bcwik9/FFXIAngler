import cv2 as cv
import numpy as np
import time
from datetime import datetime
from windowcapture import WindowCapture
import keyboard
#import functools
import random
import win32gui
import yaml
import atexit
import winsound
import os


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
# You didn't catch anything.
# <PLAYERNAME> caught a crayfish, but cannot carry any more items.
# <PLAYERNAME> regretfully releases
# <PLAYERNAME>'s fishing skill rises 0.1 points.
# <PLAYERNAME>'s fishing skill reaches level 13.
# This strength... You get the sense that you are on the verge of an epic catch!
# You can't fish without a rod in your hands.
# use /sigh when inventory is full
# alert if taking damage
# Whatever caught the hook was too small to catch with this rod.
# ... too big

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
max_time_limit_minutes = settings.get('max_time_limit', -1)

# initialize the WindowCapture class
wincap = WindowCapture(ffxi_window_name)
# Target Images
gold_img = cv.imread('./pics/gold.png', cv.IMREAD_UNCHANGED)
silver_img = cv.imread('./pics/silver.png', cv.IMREAD_UNCHANGED)

# Set initial values
state = {
    'start_time': time.time(),
    'fishing': False,
    'fish_on_line': False,
    'allow_monsters': settings.get('allow_monsters', False) == True,
    'allow_items': settings.get('allow_items', False) == True,
    'allow_delete_items': settings.get('allow_delete_items', False) == True,
    'attempt_to_catch_too_long': settings.get('attempt_to_catch_too_long', False) == True,
    'delete_item_catch_interval': int(settings.get('delete_item_catch_interval', 0)),
    'num_catches_without_delete': 0,
    'num_items_to_delete': int(settings.get('num_items_to_delete', 1)),
    'chat_log_file_name': '',
    'last_message_read': None,
    'last_arrow_found_at': None,
    'last_cast_at': None,
    'last_fish_on_line_at': None,
    'bait_failure_count': 0,
    'stats': {
        'fish_caught': 0,
        'skill_rise': 0.0,
        'skill_level': 'Unknown',
        'num_casts': 0,
        'fish': {},
        'catch_rate': 0.0
    },
    # Lower this value if you get lots of false positives
    # Raise this value if you get no matches
    'threshold': 0.017,
}
# Get the handle of the FFXI window
hwnd = win32gui.FindWindow(None, ffxi_window_name)
if hwnd == 0:
    raise Exception(f"Window with title '{ffxi_window_name}' not found")

# Skip monsters, items, and other stuff by reading logs
def handle_logs(skip_actions=False):
    month = datetime.now().month
    file_name = f'\\{ffxi_window_name}_{datetime.now().year}.{datetime.now().month:02d}.{datetime.now().day:02d}.log'
    # Check if the log file exists
    if not os.path.exists(path + file_name):
        print(f"Log file not found. Using last known chat log file name. Maybe day switched (12am)?")
        file_name = state['chat_log_file_name']
    logs = open(path + file_name, 'rb')
    log_lines = [line.decode('utf-8', errors='ignore') for line in logs.readlines()[-10::]]
    logs.close()

    if state['chat_log_file_name'] != file_name:
        # new day, new chat log
        state['chat_log_file_name'] = file_name
        state['last_message_read'] = None

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

    # Return if we were only setting up messages
    if skip_actions:
        return

    # Return if there's nothing new
    if not new_messages:
        return

    # Iterate though messages and make them searchable
    searchable_new_messages = b''.join([line.encode('utf-8') for line in new_messages])

    skill_rise = b"fishing skill rises"
    skill_rise_check = skill_rise in searchable_new_messages
    if skill_rise_check:
        print('Fishing skill rose')
        # TODO: does this rise more that 0.1 ever?
        # Add a small decimal to account for python math addition errors
        state['stats']['skill_rise'] = round(state['stats']['skill_rise'] + 0.100001, 1)
        if state['stats']['skill_level'] != 'Unknown':
            state['stats']['skill_level'] = round(state['stats']['skill_level'] + 0.100001, 1)

    skill_level_up = b"skill reaches level "
    skill_level_up_check = skill_level_up in searchable_new_messages
    if skill_level_up_check:
        # Get the level from the message
        level = searchable_new_messages.split(skill_level_up)[1].split(b'.')[0].decode('utf-8')
        print(f"Skill leveled up to {level}!")
        state['stats']['skill_level'] = int(level)

    inventory_full = f"{ffxi_window_name} regretfully releases".encode('utf-8')
    inventory_full_check = inventory_full in searchable_new_messages
    if inventory_full_check:
        if(state['allow_delete_items']):
            print('*** INVENTORY FULL - DELETING ITEMS ***')
            delete_items()
        else:
            print('*** INVENTORY FULL - EXITING ***')
            focus_window()
            send_keypress('esc')
            time.sleep(6.2)
            send_keypress('esc')
            sound_alarm()
            logout()
            

    tell_msg = b'>> '
    tell_msg_check = tell_msg in searchable_new_messages
    cant_fish_here = b'You cannot fish here'
    cant_fish_here_check = cant_fish_here in searchable_new_messages
    if tell_msg_check or cant_fish_here_check:
        if tell_msg_check:
            print('*** PLAYER SENT TELL MESSAGE DETECTED - EXITING ***')
        elif inventory_full_check:
            print('*** INVENTORY FULL - EXITING ***')
        elif cant_fish_here_check:
            print('*** NOT IN A FISHABLE AREA - EXITING ***')
        focus_window()
        send_keypress('esc')
        time.sleep(6.2)
        send_keypress('esc')
        sound_alarm()
        logout()

    # Check if fish was caught. If so, display the name of the fish
    caught_fish = f"{ffxi_window_name} caught a".encode('utf-8')
    caught_fish_check = caught_fish in searchable_new_messages
    if caught_fish_check:
        # Get the fish name from the message
        fish_name = searchable_new_messages.split(caught_fish)[1].split(b'!')[0].decode('utf-8').strip()
        # remove leading chars for 'an'
        if fish_name.startswith("n "):
            # remove first two leading chars
            fish_name = fish_name[2:]
        print(f"Caught a {fish_name}")
        if fish_name in state['stats']['fish']:
            state['stats']['fish'][fish_name] += 1
        else:
            state['stats']['fish'][fish_name] = 1
        state['stats']['fish_caught'] += 1
        print_stats()            
        #state['fishing'] = False
        state['fish_on_line'] = False
        # Check if we need to delete items from inventory
        state['num_catches_without_delete'] += 1
        if state['allow_delete_items'] and state['delete_item_catch_interval'] > 0 and state['num_catches_without_delete'] >= state['delete_item_catch_interval']:
            delete_items()
            state['num_catches_without_delete'] = 0


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
    gave_up = b'You give up'
    gave_up_check = gave_up in searchable_new_messages
    not_enough_skill = b"positive you don\'t have enough skill"
    not_enough_skill_check = not_enough_skill in searchable_new_messages
    bad_feeling = b'You have a bad feeling about this one'
    bad_feeling_check = bad_feeling in searchable_new_messages

    if (monster_check and not state['allow_monsters']) or (item_check and not state['allow_items']) or terrible_check or no_catch_check or lost_catch_check or gave_up_check or bad_feeling_check:
        if no_catch_check:
            print('No catch')
        elif lost_catch_check:
            print('Lost catch')
        elif terrible_check:
            print('Terrible feeling, ignoring')
        elif gave_up_check:
            print('Gave up')
        else:
            print('Monster or item, ignoring')
        focus_window()
        time.sleep(1)
        send_keypress("esc")
        state['fishing'] = False
        state['fish_on_line'] = False
        print_stats()
        return

    if not_enough_skill_check:
        print('Not enough skill, ignoring')
        focus_window()
        send_keypress("esc")
        time.sleep(1.2)
        state['fishing'] = False
        state['fish_on_line'] = False
        return

    fish_on_line = b'Something caught the hook!'
    fish_on_line_check = fish_on_line in searchable_new_messages or terrible_check or item_check
    if fish_on_line_check:
        print('Fish on line')
        state['fish_on_line'] = True
        state['fishing'] = False
        state['last_fish_on_line_at'] = time.time()
        state['last_arrow_found_at'] = time.time()
        state['bait_failure_count'] = 0
        return

    no_bait = b'You can\'t fish without bait on the hook.'
    no_bait_check = no_bait in searchable_new_messages
    if no_bait_check:
        print('No bait, trying to equip more with CTRL+2')
        state['bait_failure_count'] += 1
        if state['bait_failure_count'] >= 3:
            print('*** NO BAIT AVAILABLE - EXITING ***')
            send_keypress('esc')
            sound_alarm()
            logout()
        focus_window()
        send_keypress('esc')
        time.sleep(0.5)
        send_keypress('ctrl+2')
        # TODO: Verify bait was equipped: "Equipment changed."
        state['fishing'] = False
        state['fish_on_line'] = False
        return
    
def cast():
    if not state['fishing']:
        print("Casting with CTRL+1")
        state['stats']['num_casts'] += 1
        focus_window()
        send_keypress('esc')
        time.sleep(5)
        send_keypress('ctrl+1')
        state['fishing'] = True
        state['fish_on_line'] = False
        state['last_cast_at'] = time.time()
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
            state['threshold'] -= 0.003
        else:
            num_passed += 1
            if num_passed >= 15:
                calibrating = False

    # add buffer to threshold to be safe
    if state['threshold'] > 0.01:
      state['threshold'] -= 0.006

    send_keypress('esc')

def sound_alarm():
    # Play an audible sound a few times
    for _ in range(5):
        winsound.Beep(1000, 750)
        winsound.Beep(1300, 750)
        winsound.Beep(1500, 750)

def logout():
    # Logout of the game
    print("Logging out")
    send_keypress("enter")
    time.sleep(5)
    send_keypress("esc")
    time.sleep(5)
    send_keypress("esc")
    time.sleep(0.5)
    keypress_series('/logout', True)
    time.sleep(0.5)
    send_keypress("enter")
    exit()

def print_stats():
    # Print out the stats
    # update catch rate
    state['stats']['catch_rate'] = f"{int(state['stats']['fish_caught'] / state['stats']['num_casts'] * 100.0)}%"

    # update elapsed time
    state['stats']['elapsed_time'] = f"{int((time.time() - state['start_time']) / 60)} min"

    print(f"{state['stats']}")

def keypress_series(keypress_str, open_chat=False):
    send_keypress('esc')
    time.sleep(0.3)
    if open_chat:
        # Open the chat window
        send_keypress("space")
        time.sleep(0.5)

    for char in keypress_str:
        send_keypress(char)
        time.sleep(0.3)

def delete_items():
    # Delete items from the inventory.
    # IMPORTANT: Must disable auto inventory sorting, so
    # most recent items are last (at bottom) in inventory.
    focus_window()
    print("Deleting items")
    time.sleep(5)
    # open inventory window
    for _ in range(2):
        send_keypress('esc')
        time.sleep(1)
    send_keypress('ctrl+i')
    time.sleep(1)
    # scroll to last items
    for _ in range(8):
        send_keypress('l')
        time.sleep(0.3)
    # delete items
    for _ in range(state['num_items_to_delete']):
        send_keypress('enter')
        time.sleep(0.7)
        send_keypress('k')
        time.sleep(0.7)
        send_keypress('enter')
        time.sleep(0.7)
        send_keypress('i')
        time.sleep(0.7)
        send_keypress('enter')
        time.sleep(2)
    # close inventory
    time.sleep(0.7)
    send_keypress('esc')
    time.sleep(0.7)
    send_keypress('esc')


### MAIN START ###
# print status when the bot exits
atexit.register(print_stats)

# If item deletion is enabled, warn the user
if state['allow_delete_items']:
    print("*** WARNING: ITEM DELETION ENABLED ***")
    print("Item deletion is enabled. Make sure you have your keybinds set correctly, automatic inventory sorting DISABLED, and double-check your inventory space!")
    if state['num_items_to_delete'] > state['delete_item_catch_interval']:
        print("*** BAD CONFIGURATION: num_items_to_delete > delete_item_catch_interval. This will result in your inventory being deleted. The interval must be GREATER than the number of items being deleted. ***")
    sound_alarm()
    time.sleep(1)

# look at the window
focus_window()

# calibrate screen sensitivity
calibrate_sensitivity()
print(f"Calibrated threshold: {state['threshold']}")
while(False):
    print(f"{check_for_fish_arrows()}")

# set up logs
handle_logs(True)

# reset vars
state['fishing'] = False
state['fish_on_line'] = False
max_time_limit_secs = max_time_limit_minutes * 60

# Main loop
while(True):
    # Log out after certain period of time (if enabled)
    if max_time_limit_minutes > 0 and (time.time() - state['start_time']) >= max_time_limit_secs:
        print("** Max runtime limit reached, logging out **")
        logout()

    # Check logs for important messages
    #if state['fishing'] and not state['fish_on_line']:
    handle_logs()

    # Fish!
    if not state['fishing'] and not state['fish_on_line']:
        cast()

    # Make sure we haven't been waiting for a fish to bite too long
    if state['fishing'] and not state['fish_on_line'] and (time.time() - state['last_cast_at']) >= 30:
        print("**Issue detected**: Waiting for bite too long. Recasting.")
        send_keypress("esc")
        time.sleep(1)
        state['stats']['num_casts'] -= 1
        state['fishing'] = False
        state['fish_on_line'] = False

    # Make sure we haven't been trying to catch a fish for too long
    if state['fish_on_line'] and state['last_fish_on_line_at'] and (time.time() - state['last_fish_on_line_at']) >= 26:
        print("**Issue detected**: Fishing too long.")
        focus_window()
        if state['attempt_to_catch_too_long']:
            send_keypress("enter")
            time.sleep(2)
        send_keypress("esc")
        time.sleep(1)
        state['fish_on_line'] = False
        state['fishing'] = False
        calibrate_sensitivity()

    # Check logs for important messages
    #if state['fishing'] and not state['fish_on_line']:
    #handle_logs()

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
        print("No more arrows detected, catching fish...")
        random_wait = random.choice([0.2, 0.3, 0.4])
        time.sleep(random_wait)
        send_keypress("enter")
        time.sleep(0.2)
        send_keypress("enter")
        state['fish_on_line'] = False
        state['fishing'] = False
        time.sleep(2)