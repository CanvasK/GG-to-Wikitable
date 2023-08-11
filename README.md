# GG-to-Wikitable
Retrieves data from start.gg and creates a wikitable. For SSBWiki editors.

Tested on Python 3.7. Other versions have not been tested and cannot be guaranteed to work correctly.

# How to use
## Authorization
A start.gg authorization code will be needed for operation. The authorization code should go in a file called `auth.txt` that is in the same directory as `main.py`. This file is automatically created when the script is first run and there will be a prompt to add your code (this will also add your code to the file, skipping this step for future runs).

## Config
Settings for the script are in `config.cfg`.

### request
`MaxPlacement` and `MaxPages` will terminate the program early (if set to `-1`, it will continue until another part of the program stops it). The former is useful for creating smaller tables. The latter is useful for testing to ensure the query works as only one page is necessary to check.

### output
`MaxLinked` will stop the program from using {{Sm}} for players if they ranked lower than the value. This is to prevent redlinks for players that have poor results and thus will not likely be notable enough for an article.

`MaxDQ` will mark players as a "full DQ" if they meet or exceed the value.

`OutputInfo` will output some basic info about the event, similar to what is printed during operation.

## Running
The events you want to make tables for go in `targets.txt`. Each event requires its own line. A full URL or just the slug are valid inputs (if the URL is `https://www.start.gg/tournament/evo-2019/event/super-smash-bros-ultimate`, the slug is `tournament/evo-2019/event/super-smash-bros-ultimate`).

If only the tournament's URL/slug is used, you will be prompted to select which event(s) to use (only events with game IDs defined in `game IDs.txt` will be shown).

`main.py` should be able to be run simply by double-clicking it in the directory explorer. A table will be generated in `output.txt` in the `outputs` directory with the subdirectories matching the event's slug; this file and directories are automatically created if one doesn't exist and the file is cleared if one does exist. An `info.txt` file will also be created if `OutputInfo=True`.