# FFXIAngler

Simple OpenCV based fishing bot for FFXI

## Notes on usage

- Download this repository

- Copy `settings.example.yml` file to `settings.yml`, and change the required values such as your FFXI window name and screen width

- Run the bot with `py main.py` or `python3 main.py`
  - You may have to install dependencies such as `pip install pyyaml`

- Cancel bot by interupting (ctrl + c in the terminal window)

- Macros required:
  - Ctrl + 1 = '/fishing'
  - Ctrl + 2 = '/equip Ammo "<YOUR BAIT HERE>"'

- As the bot reads the chat log to release monsters/items Ashita Logs plugin is necessary: <https://docsv3.ashitaxi.com/addons/logs>

- I have tested this on private servers using 1280 * 720 windowed mode and it works without error until bait is completely used

- Found it best to point the screen down at the feet of the char to minimise changing scenery in the background which may confuse the bot

- Any improvements / feedback welcome, looking to add bait re-equipping in the future

## Thanks

Big thanks to [Gakkun89](https://github.com/Gakkun89) for their original work on this bot.

Windowcapture code taken from: https://github.com/learncodebygaming/opencv_tutorials
