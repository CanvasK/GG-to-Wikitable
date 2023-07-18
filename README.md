# GG-to-Wikitable
Retrieves data from start.gg and creates a wikitable. For SSBWiki editors.

Tested on Python 3.7. Other versions have not been tested and cannot be guaranteed to work correctly.

# How to use
## Authorization
A file called `auth.txt` will need to be created in the same directory as main.py with your own start.gg authorization code for the program to work.

## Config
Settings for the script are in `config.cfg`.

The most important configs are `EventSlug` and `EventType`.
- `EventSlug` is the link to the event. If the full URL is `https://www.start.gg/tournament/evo-2018/event/evo-2018-1`, then the slug is `tournament/evo-2018/event/evo-2018-1`.
- `EventType` is the whether the event is singles or doubles.

Most other settings are described within the config file.

## Running
`main.py` should be able to be run simply by double-clicking it in the directory viewer. A table will be generated in `output.txt`; this file is automatically created if one doesn't exist and cleared if one does exist.