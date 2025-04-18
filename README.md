# FFXIAngler

Simple OpenCV based fishing bot for FFXI

## Notes on usage

- Download this repository

- Copy `settings.example.yml` file to `settings.yml`, and change the required values such as your FFXI window name and screen width

- Make sure you have dependencies installed, or you'll get an error
  - install python (DO NOT USE the windows store version of python - download it from the python site)
    - if you get an error running python, you might have to modify your PATH environment variable to point to the correct location of python and pip
  - run `python -m pip install --upgrade pip setuptools wheel`
  - if you get an error when running the script, it's likely you're missing a package. Just look at what package it's complaining about and run: `pip install WHATEVER_PACKAGE_YOURE_MISSING`
    - you probably need to run this: `pip install opencv-python pywin32 keyboard pyyaml`

- Run the bot with `py main.py` or `python3 main.py`
  - You may have to install dependencies such as `pip install pyyaml`
  - If FFXI is not doing anything, you may have to run the script as an administrator. Open your command terminal using "Run as an administrator" then run the script.

- Bot requires the FFXI window to be in focus (ie. you can't run this in the background)

- Cancel bot by interupting (ctrl + c in the terminal window)

- If bot is not reliably catching fish, try repositioning your camera and restarting the bot

- Macros required:
  - Ctrl + 1 = `/fishing`
  - Ctrl + 2 = `/equip Ammo "YOUR BAIT"`

- As the bot reads the chat log to release monsters/items Ashita Logs addon is necessary: <https://docsv3.ashitaxi.com/addons/logs>.

- The bot requires timestamps on the chat messages. Enable the [Ashita timestamp addon](https://github.com/AshitaXI/Ashita-v4beta/tree/main/addons/timestamp)

- I have tested this on private servers using 1280 * 720 windowed mode and it works without error until bait is completely used

- Found it best to point the screen down at the feet of the char to minimise changing scenery in the background which may confuse the bot

- Any improvements / feedback welcome, looking to add bait re-equipping in the future

## Thanks

Big thanks to [Gakkun89](https://github.com/Gakkun89) for their original work on this bot.

Windowcapture code taken from: https://github.com/learncodebygaming/opencv_tutorials
