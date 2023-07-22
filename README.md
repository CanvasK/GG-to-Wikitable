# GG-to-Wikitable
Retrieves data from start.gg and creates a wikitable. For SSBWiki editors.

Tested on Python 3.7. Other versions have not been tested and cannot be guaranteed to work correctly.

# How to use
## Authorization
A file called `auth.txt` will need to be created in the same directory as main.py with your own start.gg authorization code for the program to work.

## Config
Settings for the script are in `config.cfg`.

###request
####Mode (single or bulk) will cause certain configs to be ignored.
`Mode` controls whether the program gets data for a single event or multiple. "Single" mode is useful for fine-tuned settings or for testing. "Bulk" mode is useful for dealing with multiple events in a tournament or even multiple tournaments. 
#####single
In single mode, the most important configs are `EventSlug` and `EventType`.
- `EventSlug` is the link to the event. If the full URL is `https://www.start.gg/tournament/evo-2018/event/evo-2018-1`, then the slug is `tournament/evo-2018/event/evo-2018-1`.
- `EventType` is the whether the event is singles or doubles.

#####bulk
In bulk mode, the configs `EventSlug` and `EventType` are ignored. These are instead defined in `bulk.txt` in comma-separated format (e.g. "tournament/evo-2018/event/evo-2018-1, singles")
####MaxPlacement and MaxPages
`MaxPlacement` and `MaxPages` will terminate the program early (if set to `-1`, it will continue until another part of the program stops it). The former is useful for creating smaller tables. The latter is useful for testing to ensure the query works as only one page is necessary to check.

###output
`MaxLinked` will stop the program from using {{Sm}} for players if they ranked lower than the value. This is to prevent redlinks for players that have poor results and thus will not likely be notable enough for an article.

`MaxDQ` will mark players as a "full DQ" if they meet or exceed the value.

## Running
`main.py` should be able to be run simply by double-clicking it in the directory viewer. A table will be generated in `output.txt` in the `outputs` directory with the subdirectories matching the event's slug; this file and directories are automatically created if one doesn't exist and the file is cleared if one does exist.