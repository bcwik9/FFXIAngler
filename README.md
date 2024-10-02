# FFXIAngler

Simple OpenCV based fishing bot for FFXI

## Notes on usage

- I am not a Python dev so this might be inefficient and ugly... but it works

- Macros required: Ctrl + 1 = '/fishing'

- As the bot reads the chat log to release monsters/items Ashita Logs plugin is necessary: <https://docsv3.ashitaxi.com/addons/logs>

- Again as the bot looks at the last 2 lines of the log try to minimise log spam (filter chat) and unequip linkshell is recommended

- I have tested this on private servers using 1280 * 720 windowed mode and it works without error until bait is completely used

- I have only tested this at the Knightwell fishing for moat carp, other areas most likely work but haven't been tested and may need differing thresholds

- Found it best to point the screen down at the feet of the char to minimise changing scenery in the background which may confuse the bot

- Any improvements / feedback welcome, looking to add bait re-equipping in the future

## Thanks

Massive thanks to https://www.youtube.com/@LearnCodeByGaming for the great beginners guide to making OpenCV bots for games.

Windowcapture code taken from: https://github.com/learncodebygaming/opencv_tutorials
