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

`PerPage` sets how many entries are returned in each page. Larger values mean fewer pages and thus fewer requests, but start.gg will spend longer preparing the data. The inverse for smaller values; more pages but start.gg sends the data faster. Events with complex formats (e.g. Waterfall or Round Robin) tend to have more complex data, and start.gg has a limit on how "complex" the data can be before giving up (1000 objects). If the data is too complex, setting this value lower will also lower the complexity.

### output
`MaxLinked` will stop the program from using {{Sm}} for players if they ranked lower than the value. This is to prevent redlinks for players that have poor results and thus will not likely be notable enough for an article.

`MaxDQ` will mark players as a "full DQ" if they meet or exceed the value.

`OutputInfo` will output some basic info about the event to `info.txt`, similar to what is printed during operation.

`GoofyTagNote` will append "< ref >Entered as "[TAG]"< /ref >" if the start.gg tag is different (excluding punctuation, spacing, and casing) from the SmashWiki tag. These tags will be noted in `info.txt` regardless.

### format
The following values can be used for the format output. They must be surrounded in curly brackets (e.g. `{placement}`). Values with a "#" in them indicate that there is more than one value to choose from (e.g. the second `userID#` value would be `{userID2}`); leaving the "#" or using an out-of-range value will result in the format string being unmodified.
* `placementRaw`: Placement number without ordinals or DQ formatting.
* `placement`: Placement after ordinals and DQ formatting
* `entrantID`: ID for the "entrant" (player/team) at the specific event. Little use outside the event.
* `entrantName`: Like previous, but for player/team name.
* `participantID#`: ID for the "participant" (player(s) within "entrant") at the specific event. Little use outside the event.
* `participantGamerTag#`: Gamer Tag used at the specific event.
* `userID#`: Global start.gg ID. Every registered user has one, but not every player listed at an event is a user.
* `userDiscriminator#`: Global start.gg identifier in the URL ("`start.gg/user/<discriminator>`"). Every registered user has one, but if the account is private this value is empty.
* `userCountry#`: The country listed on the user's account. Global value, meaning it isn't possible to get country of a user for a specific event (i.e. if a user lived in the UK and went to an event there, and currently lives in the USA, their country for that old event will be USA).
* `playerName#`: Player's name after formatting.
* `playerChars#`: Player's characters after formatting. Virtually useless but needed for proper DQ formatting.

## Running
The events you want to make tables for go in `targets.txt`. Each event requires its own line. A full URL or just the slug are valid inputs (if the URL is `https://www.start.gg/tournament/evo-2019/event/super-smash-bros-ultimate`, the slug is `tournament/evo-2019/event/super-smash-bros-ultimate`).

If only the tournament's URL/slug is used, you will be prompted to select which event(s) to use (only events with game IDs defined in `game IDs.txt` will be shown).

`main.py` should be able to be run simply by double-clicking it in the directory explorer. A table will be generated in `output.txt` in the `outputs` directory with the subdirectories matching the event's slug; this file and directories are automatically created if one doesn't exist and the file is cleared if one does exist. An `info.txt` file will also be created if `OutputInfo=True`.