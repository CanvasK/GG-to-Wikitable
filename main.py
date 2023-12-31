import helper_functions
import helper_classes
import helper_exceptions
import json
import re
import os
import configparser
import time
import datetime


def print_time():
	print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def end_pause():
	time.sleep(config.getint('other', 'EndPause'))


print_time()
decreasingSleep = helper_classes.Sleeper(start_time=time.time(), end_time=time.time(), target_delay=0.8)
rePunctuationRemove = re.compile(r"[^\w]")

gameNameByStartGGID = dict()
with open("game IDs.txt") as g:
	for line in g:
		if not line.startswith("#"):
			key, value = line.split(",", 1)
			key = int(key)
			value = [v.strip() for v in value.split(",")]
			gameNameByStartGGID[key] = {"full": value[0], "short": value[1]}

playerNamebyStartGGDiscrim = dict()
with open("gg discriminator to wiki.tsv") as d:
	for line in d:
		if not line.startswith("#"):
			key, value = line.split("\t", 1)
			key = str(key)
			value = [v.strip() for v in value.split("\t")]
			if len(value) == 1:
				playerNamebyStartGGDiscrim[key] = [value[0], None]
			else:
				playerNamebyStartGGDiscrim[key] = [value[0], value[1]]

config = configparser.ConfigParser()
config.read('config.cfg')

if os.path.exists("auth.txt"):
	with open("auth.txt", 'r+') as a:
		authToken = a.read().strip()
		if len(authToken) == 0:
			print("No token found in auth.txt.")
			authInput = input("Paste your authorization code here and press enter: (leave blank to close)\n")
			if len(authInput.strip()) == 0:
				exit()
			else:
				authToken = authInput.strip()
				a.write(authToken)
else:
	with open("auth.txt", 'a') as a:
		print("No token found in auth.txt.")
		authInput = input("Paste your authorization code here and press enter: (leave blank to close)\n")
		if len(authInput.strip()) == 0:
			exit()
		else:
			authToken = authInput.strip()
			a.write(authToken)

queryEventFromTrn = """
query ($slug: String!, $gameIDs: [ID]) {
	tournament (slug: $slug) {
		events (filter: {videogameId: $gameIDs}) {
			name
			slug
			type
			videogame {
				id
				name
			}
		}
	}
}
"""

queryOnceData = """
query ($eventSlug: String!) {
	event (slug: $eventSlug) {
		id
		name
		slug
		tournament { name }
		videogame { id }
		startAt
		createdAt
		updatedAt
		state
		prizingInfo
		isOnline
		numEntrants
		teamRosterSize { maxPlayers }
		type
		# standings (query: {page: 1, perPage: 100}) { pageInfo { totalPages } }
		phases {
			name
			groupCount
			phaseGroups (query: {perPage: 50, page: 1}) {
				nodes { bracketUrl }
			}
		}
	}
}
"""

queryStandings = """
query ($eventSlug: String!, $page: Int!, $perPage: Int!) {
	event(slug: $eventSlug) {
		standings(query: {page: $page, perPage: $perPage}) {
			nodes {
				placement
				entrant {
					id
					name
					participants {
						id
						gamerTag
						user {
							id
							discriminator
							location { country }
						}
					}
					paginatedSets (page: 1, perPage: 50, sortType: RECENT) {
						nodes {
							displayScore
							winnerId
							round
						}
					}
				}
			}
		}
	}
}
"""

# entrant {name} = At-the-time tag
# team>members>player {gamerTag} = Current tag
# team>members>participant {gamerTag} = At-the-time tag


# ===================================== Events =====================================

eventsToQueryList = []
mainSettings = {
	"MaxPlacement": config.getint('request', 'MaxPlacement'),
	"MaxPages": config.getint('request', 'MaxPages'),
	"PerPage": config.getint('request', 'PerPage'),
	"TableHeaderSingle": config.get('format', 'TableHeaderSingle'),
	"TableRowSingle": config.get('format', 'TableRowSingle'),
	"TableHeaderDouble": config.get('format', 'TableHeaderDouble'),
	"TableRowDouble": config.get('format', 'TableRowDouble'),
	"MaxLinked": config.getint('output', 'MaxLinked'),
	"MaxDQ": config.getint('output', 'MaxDQ'),
	"OutputInfo": config.getboolean('output', 'OutputInfo'),
	"GoofyTagNote": config.getboolean('output', 'GoofyTagNote')
}

with open("targets.txt", 'r', encoding='utf-8') as t:
	TempEventsToQuery = []
	for line in t:
		tempSettings = mainSettings.copy()

		if not line.startswith("#"):  # Ignore comments
			if len(line) > 0:  # Skip blank lines
				if ";" in line:  # If the line contains config info
					slug, setting = line.split(";", 1)

					for s in setting.split(","):  # Configs are comma-separated
						for k in tempSettings:  # For each key in the settings
							if s.strip().startswith(k):  # If the current config starts with the key
								_s = s.split("=")[-1].strip()
								# Try to cast to a reasonable type
								try:
									tempSettings[k] = int(_s)
								except ValueError as e:
									print(e)
									try:
										tempSettings[k] = bool(_s)
									except ValueError:
										tempSettings[k] = str(_s)
				# If no config, then line is likely just slug
				else:
					slug = line.strip()
				try:
					slug = helper_functions.gg_slug_cleaner(slug)
				except helper_exceptions.SlugMissingError as e:
					print("URL/slug field is empty. Make sure there is a URL/slug at the beginning of the line in targets.txt")
					continue
				# Add slug and settings to dict and add the dict to the list
				# Settings default to config file if no semicolon is found
				TempEventsToQuery.append({"slug": slug, "settings": tempSettings})
	eventsToQueryList = TempEventsToQuery.copy()

eventsToQueryAppend = []
eventsToRemove = []

for target in eventsToQueryList:
	slug = target["slug"]

	# If input slug only has 1 slash, then it must be a tournament link.
	# There can't be any other counts than 1 or 3 as a previous function
	# strips anything >3, and strips the 2nd down to 1 if there is no 3 slashes
	if slug.count("/") == 1:
		decreasingSleep.sleep(end_time=time.time())
		# Using the slug, get a list of events
		# Only events with IDs in `game IDs.txt` are returned
		variables = {"slug": slug, "gameIDs": list(gameNameByStartGGID)}
		eventFromTrn = helper_functions.base_gg_query(query=queryEventFromTrn, variables=variables, auth=authToken)

		eventsTemp = eventFromTrn['data']['tournament']['events']

		print("-" * 5)
		print("Tournament was used as a target. (" + str(slug) + ")\nInput the listed number of the event to generate a table for.\nTo select multiple, separate each number with a comma (e.g. 1, 3).\n(Leave blank to skip)")
		print("-" * 5)

		# Show the list of valid events to choose from
		# 1-indexed to be intuitive for non-programmers. Index is decremented later
		eventIndexer = 1
		eventsToSelectFrom = []

		for e in eventsTemp:
			eventsToSelectFrom.append({"name": e['name'], "slug": e['slug']})
			print("{c}: {n} | {s}".format(c=eventIndexer, n=e['name'], s=e['slug']))
			eventIndexer += 1

		# Get user input
		eventsSelected = input()
		# Store the tournament to be removed later to prevent the loop from terminating early
		eventsToRemove.append(target)
		# If the input is nothing, then skip
		if len(eventsSelected.strip()) == 0:
			continue
		else:
			# If the user entered multiple numbers
			eventsSelected = eventsSelected.split(",")
			for s in eventsSelected:
				try:
					# Add selected event to temporary list to prevent the loop from being longer than intended
					# Don't add the vent if it is already in the list
					if eventsToQueryAppend not in eventsToQueryList:
						# Decrement index by 1 as the input is 1-indexed for UX reasons
						eventsToQueryAppend.append({"slug": eventsToSelectFrom[int(s) - 1]['slug'], "settings": target["settings"]})
				except ValueError:
					print(str(s) + " is not a number")
					pass
				except IndexError:
					print(str(s) + " is not an option")
					pass

	else:
		pass

# Remove tournament slugs from list as they won't give good data
for t in eventsToRemove:
	eventsToQueryList.remove(t)

# Add selected events to the list
eventsToQueryList.extend(eventsToQueryAppend)

# If the list of targets is still empty after checking tournaments, ask for an event
if len(eventsToQueryList) == 0:
	print("targets.txt is empty. Please add events to targets.txt or enter an event URL below: (leave blank to exit)")
	targetInput = input()
	if len(targetInput.strip()) == 0:
		exit()
	else:
		eventsToQueryList.append({"slug": helper_functions.gg_slug_cleaner(targetInput), "settings": mainSettings.copy()})
print(eventsToQueryList)


# ===================================== Query =====================================
# Go through every event
for event in eventsToQueryList:

	print_time()
	print("="*10 + " Starting queries")

	activeSettings = event["settings"]
	activeSlug = event["slug"]

	# Data about the event that doesn't change
	eventMainData = helper_functions.base_gg_query(query=queryOnceData, variables={"eventSlug": activeSlug}, auth=authToken)['data']['event']

	# Info about the event that doesn't change
	eventMainInfo = {
		"Tournament": "",
		"Event": "",
		"URL": "",
		"Game ID": 1,
		"Game": "",
		"Entrant count": 0,
		"Team size": 1,
		"Type": "",
		"Start datetime": 0,
		"Is online": False,
		"Status": "",
		"DQ count": {"Full": 0, "Losers": 0, "Winners": 0},
		"Prize info": "",
		"Goofy tags": {"GG NAME": "WIKI NAME"}
	}

	# Get brackets and keep only ones with 1 group
	phaseData = eventMainData['phases']
	phaseBrackets = []
	for phase in phaseData:
		if phase['groupCount'] == 1:
			phaseBrackets.append("[{0} {1}]".format(phase['phaseGroups']['nodes'][0]['bracketUrl'], phase['name'] if "bracket" in phase['name'].lower() else phase['name'] + " Bracket"))

	# Get game ID
	eventMainInfo["Game ID"] = eventMainData['videogame']['id']

	# Get size of teams
	if eventMainData['teamRosterSize'] is not None:
		eventMainInfo["Team size"] = int(eventMainData['teamRosterSize']['maxPlayers'])

	# Determine query based on team size
	if eventMainInfo["Team size"] == 1 or eventMainInfo["Team size"] == 2:
		targetQuery = queryStandings
	else:
		print("Unsupported type")
		end_pause()
		continue

	# Initialize info about the event
	eventMainInfo["Tournament"] = eventMainData['tournament']['name']
	eventMainInfo["Event"] = eventMainData['name']
	eventMainInfo["URL"] = "https://www.start.gg/" + eventMainData['slug']
	eventMainInfo["Game"] = gameNameByStartGGID[eventMainData['videogame']['id']]["full"]
	eventMainInfo["Entrant count"] = eventMainData['numEntrants']
	eventMainInfo["Status"] = eventMainData['state']
	if eventMainData['type'] == 1:
		eventMainInfo["Type"] = "Single Elimination"
	elif eventMainData['type'] == 5:
		eventMainInfo["Type"] = "Double Elimination"
	eventMainInfo["Start datetime"] = time.strftime("%Y-%m-%d %H:%M:%S+00:00 (UTC)", time.gmtime(int(eventMainData['startAt'])))
	eventMainInfo["Is online"] = eventMainData['isOnline']
	if eventMainData['prizingInfo']['enablePrizing']:
		eventMainInfo["Prize info"] = eventMainData['prizingInfo']

	# Print info about the event
	print("tournament:", eventMainInfo["Tournament"])
	print("event:", eventMainInfo["Event"])
	print(eventMainInfo["URL"])
	print(eventMainInfo["Start datetime"])
	print("game:", eventMainInfo["Game"] + " (" + str(eventMainInfo["Game ID"]) + ")")
	print("entrants:", eventMainInfo["Entrant count"])
	print("type:", eventMainInfo["Type"])
	print("roster size:", eventMainInfo["Team size"])
	print("online:", eventMainInfo["Is online"])
	print("prize info:", eventMainInfo["Prize info"])
	print()

	standingsList = list()
	currentPageCount = 1

	print("Settings:", activeSettings)

	# ===================================== Pages =====================================
	# Loop through pages until limit is reached
	while True:
		queryStartTime = time.time()

		eventStandingData = helper_functions.event_data_slug(slug=activeSlug, page=currentPageCount, per_page=activeSettings["PerPage"], query=targetQuery, auth=authToken)
		eventStandingListTemp = eventStandingData['standings']['nodes']

		# If the returned page is empty, then there are no more pages to go through
		if len(eventStandingListTemp) == 0:
			print("\nNo more pages")
			break

		standingsList.extend(eventStandingListTemp)

		# Only placements up to a point are documented. Stop if too many
		if activeSettings["MaxPlacement"] > 0:
			if eventStandingListTemp[-1]['placement'] > activeSettings["MaxPlacement"]:
				print("\npages:", currentPageCount)
				break

		if (activeSettings["MaxPages"] > 0) and (activeSettings["MaxPages"] == currentPageCount):
			print("\nMax pages reached")
			break

		queryEndTime = time.time()

		totalPage = eventMainInfo["Entrant count"]/activeSettings["PerPage"]
		currentPage = len(standingsList)/activeSettings["PerPage"]
		print("\rPage: {c: <4} | Response time: {t} seconds | Entrants: {e: <7,}/{ec: <7,} | Est. remaining time: {remain} seconds"
			  .format(c=currentPageCount, t=queryEndTime - queryStartTime, e=len(standingsList), ec=eventMainInfo["Entrant count"],
					  remain=decreasingSleep.avg_time*(totalPage-currentPage)), end='', flush=True)

		currentPageCount += 1
		decreasingSleep.sleep(end_time=time.time())

	# ===================================== Tables =====================================
	print()
	print("="*10 + " Queries complete ")
	print_time()
	print("="*10 + " Creating table ")

	dqOrder = []
	outputTableString = ""

	if eventMainInfo["Team size"] == 1:
		outputHeaderString = activeSettings["TableHeaderSingle"] + "\n"
		outputRowString = activeSettings["TableRowSingle"] + "\n"
	elif eventMainInfo["Team size"] == 2:
		outputHeaderString = activeSettings["TableHeaderDouble"] + "\n"
		outputRowString = activeSettings["TableRowDouble"] + "\n"
	else:
		outputHeaderString = activeSettings["TableHeaderSingle"] + "\n"
		outputRowString = activeSettings["TableRowSingle"] + "\n"

	# Handle escape characters
	outputHeaderString = bytes(outputHeaderString, "utf-8").decode('unicode_escape')
	outputRowString = bytes(outputRowString, "utf-8").decode('unicode_escape')
	if eventMainInfo["Team size"] == 1 or eventMainInfo["Team size"] == 2:
		outputTableString += outputHeaderString

		for standing in standingsList:
			playerData = {
				"placementRaw": standing['placement'],
				"placement": standing['placement'],
				"entrantID": standing['entrant']['id'],
				"entrantName": standing['entrant']['name'],
				"participantID#": [x['id'] for x in standing['entrant']['participants']],
				"participantGamerTag#": [x['gamerTag'] for x in standing['entrant']['participants']],
				"userID#": [standing['entrant']['participants'][i]['user']['id'] if standing['entrant']['participants'][i]['user'] is not None else None for i in range(len(standing['entrant']['participants']))],
				"userDiscriminator#": [standing['entrant']['participants'][i]['user']['discriminator'] if standing['entrant']['participants'][i]['user'] is not None else None for i in range(len(standing['entrant']['participants']))],
				"userCountry#": [standing['entrant']['participants'][i]['user']['location']['country'] if standing['entrant']['participants'][i]['user'] is not None and standing['entrant']['participants'][i]['user']['location'] is not None else None for i in range(len(standing['entrant']['participants']))],
				"playerName#": [],
				"playerChars#": []
			}

			playerData['placement'] = helper_functions.make_ordinal(playerData['placementRaw'])

			# Loop through each user in the team
			for t in range(len(playerData["userDiscriminator#"])):
				# If the discriminator is not empty (not private) and is in the list
				if playerData["userDiscriminator#"][t] != "" and playerData["userDiscriminator#"][t] in playerNamebyStartGGDiscrim:
					playerNameFromDiscrim = playerNamebyStartGGDiscrim[playerData["userDiscriminator#"][t]]

					compareGGNameLower = rePunctuationRemove.sub("", playerData["participantGamerTag#"][t].lower())
					compareWikiNameLower = rePunctuationRemove.sub("", playerNameFromDiscrim[0].lower())

					goofyTag = ""

					if compareGGNameLower != compareWikiNameLower:
						eventMainInfo["Goofy tags"][compareGGNameLower] = compareWikiNameLower
						if activeSettings["GoofyTagNote"]:
							goofyTag = "<ref>Entered as \"" + str(playerData["participantGamerTag#"][t]) + "\"</ref>"

					playerData['playerName#'].append(
						helper_functions.smasher_link(
							name=playerNameFromDiscrim[0], disambig=playerNameFromDiscrim[1],
							flag=playerData["userCountry#"][t],
							enable_link=playerData["placementRaw"] <= activeSettings["MaxLinked"]) + goofyTag
					)
				# Default to using start.gg tag
				else:
					playerData['playerName#'].append(
						helper_functions.smasher_link(
							name=playerData["participantGamerTag#"][t],
							flag=playerData["userCountry#"][t],
							enable_link=playerData["placementRaw"] <= activeSettings["MaxLinked"])
					)
				# Do nothing with characters for now
				playerData['playerChars#'].append("")

			# DQ stuff
			setList = standing['entrant']['paginatedSets']['nodes']
			dqJudgement, dqSets = helper_functions.dq_judge(playerData['entrantID'], setList, activeSettings["MaxDQ"])

			if dqJudgement == "pass":
				pass
			elif dqJudgement == "full":
				for t in range(len(playerData['playerName#'])):
					playerData['playerName#'][t] += " (DQ)"
					# noinspection PyTypeChecker
					eventMainInfo["DQ count"]["Full"] += 1
			else:
				if dqJudgement == "losers":
					if dqJudgement not in dqOrder:
						dqOrder.append(dqJudgement)
				# noinspection PyTypeChecker
				eventMainInfo["DQ count"]["Losers"] += 1
				if dqJudgement == "winners":
					if dqJudgement not in dqOrder:
						dqOrder.append(dqJudgement)
				# noinspection PyTypeChecker
				eventMainInfo["DQ count"]["Winners"] += 1
				playerData['placement'] += "*"*(dqOrder.index(dqJudgement) + 1)

			# If the sets played are nothing but DQs, list characters as a dash
			if dqSets.count(0) == 0:
				for t in range(len(playerData["playerChars#"])):
					playerData["playerChars#"][t] = "&mdash;"

			rowString = outputRowString
			# Replace every format string with the corresponding value
			for d in playerData:
				if "#" in d:
					for i in range(len(playerData[d])):
						rowString = rowString.replace("{"+d.replace("#", str(i+1))+"}", str(playerData[d][i]))
				else:
					rowString = rowString.replace("{"+d+"}", str(playerData[d]))

			outputTableString += rowString

		outputTableString = outputTableString.replace("||||", "|| ||")
		outputTableString += "|}"

	# Add asterisk notes to the end of the table
	if len(dqOrder) > 0:
		outputTableString += "\n"
		for d in dqOrder:
			outputTableString += "{{*}}" * (dqOrder.index(d) + 1) + "DQ'd in " + d.capitalize() + ".\n"

	# ===================================== Output =====================================
	print("="*10 + " Table complete ")
	print_time()

	headerString = "===''[[{0}]]'' {1}===\n"

	outputPath = os.path.join("outputs", str(activeSlug).replace("tournament/", "").replace("/event/", "/"))
	if not os.path.exists(outputPath):
		os.makedirs(outputPath)
		print("="*10 + "Creating directory: " + outputPath.replace("/", "\\"))

	print("="*10 + " Writing to \"" + outputPath.replace("/", "\\") + "\\output.txt\" ")

	with open(os.path.join(outputPath, "output.txt"), "w+", encoding='utf-8') as f:
		# Header and Entrants
		if eventMainInfo["Team size"] == 1:
			f.write(headerString.format(gameNameByStartGGID[eventMainInfo["Game ID"]]["full"], "singles"))
			f.write("({0:,} entrants)<br>\n".format(eventMainInfo["Entrant count"]))
		elif eventMainInfo["Team size"] == 2:
			f.write(headerString.format(gameNameByStartGGID[eventMainInfo["Game ID"]]["full"], "doubles"))
			f.write("({0:,} teams)<br>\n".format(eventMainInfo["Entrant count"]))

		# Bracket(s)
		for i in range(len(phaseBrackets)):
			# The last bracket does not get a <br>
			if i != len(phaseBrackets) - 1:
				f.write(phaseBrackets[i] + "<br>\n")
			else:
				f.write(phaseBrackets[i] + "\n")
		# Table
		f.writelines(outputTableString)

	if activeSettings["OutputInfo"]:
		with open(os.path.join(outputPath, "info.txt"), "w+", encoding='utf-8') as f:
			json.dump(eventMainInfo, f, ensure_ascii=False, indent=1)

	print("\n"*2)


print("="*10 + " Finished ")
print_time()
end_pause()
