import helper
import json
import os
import configparser
import time
import datetime


def print_time():
	print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def end_pause():
	time.sleep(config.getint('other', 'EndPause'))


print_time()
decreasingSleep = helper.Sleeper(start_time=time.time(), end_time=time.time())

gameByID = dict()
with open("game IDs.txt") as g:
	for line in g:
		if not line.startswith("#"):
			key, value = line.split(",", 1)
			key = int(key)
			value = [v.strip() for v in value.split(",")]
			gameByID[key] = value


perPageCount = 40

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

querySingles = """
query ($eventSlug: String!, $page: Int!, $perPage: Int!) {
	event(slug: $eventSlug) {
		standings(query: {page: $page, perPage: $perPage}) {
			nodes {
				placement
				player {
					id
					gamerTag
					user { location { country } }
				}
				entrant {
					id
					name
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

queryDoubles = """
query ($eventSlug: String!, $page: Int!, $perPage: Int!) {
	event(slug: $eventSlug) {
		standings(query: {page: $page, perPage: $perPage}) {
			nodes {
				placement
				entrant {
					id
					name
					team {
						name
						members {
							isCaptain
							participant {
								gamerTag
								player { user { location {country} } }
							}
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

targetEvents = []
mainSettings = {
	"MaxPlacement": config.getint('request', 'MaxPlacement'),
	"MaxPages": config.getint('request', 'MaxPages'),
	"MaxLinked": config.getint('output', 'MaxLinked'),
	"MaxDQ": config.getint('output', 'MaxDQ'),
	"OutputInfo": config.getboolean('output', 'OutputInfo')
}

with open("targets.txt", 'r', encoding='utf-8') as t:
	targetLoadTemp = []
	for line in t:
		tempSettings = mainSettings.copy()
		# Ignore comments
		if not line.startswith("#"):
			# Skip blank lines
			if len(line) > 0:
				if ";" in line:
					slug, setting = line.split(";", 1)
					for s in setting.split(","):
						for k in tempSettings:
							if s.strip().startswith(k):
								_s = s.split("=")[-1].strip()
								try:
									tempSettings[k] = int(_s)
								except ValueError as e:
									print(e)
									try:
										tempSettings[k] = bool(_s)
									except ValueError:
										continue
				else:
					slug = line.strip()
				try:
					slug = helper.gg_slug_cleaner(slug)
				except helper.SlugMissingError as e:
					print("Slug field is empty. Make sure there is a slug at the beginning of the line in targets.txt")
					continue
				targetLoadTemp.append({"slug": slug, "settings": tempSettings})
	# print("\n" * 3)
	targetEvents = targetLoadTemp

targetsNew = []
targetsRemove = []

for target in targetEvents:
	slug = target["slug"]

	if slug.count("/") == 1:
		decreasingSleep.sleep(end_time=time.time())
		variables = {"slug": slug, "gameIDs": list(gameByID)}
		eventFromTrn = helper.gg_query(query=queryEventFromTrn, variables=variables, auth=authToken)

		eventsTemp = eventFromTrn['data']['tournament']['events']
		eventSelectables = []

		for e in eventsTemp:
			eventSelectables.append({"name": e['name'], "slug": e['slug']})

		print("-" * 5)
		print("Tournament was used as a target. (" + str(slug) + ")\nInput the listed number of the event to generate a table for.\nTo select multiple, separate each number with a comma (e.g. 1, 3).\n(Leave blank to skip)")
		print("-" * 5)

		# Show the list of valid events to choose from
		# One-indexed to be intuitive for non-programmers. Index is decremented later
		eventIndexer = 1
		for e in eventSelectables:
			print("{c}: {n} | {s}".format(c=eventIndexer, n=e['name'], s=e['slug']))
			eventIndexer += 1

		selectedEvents = input()
		# Store the tournament for later to prevent the loop from terminating early
		targetsRemove.append(target)
		if len(selectedEvents.strip()) == 0:
			continue
		else:
			selectedEvents = selectedEvents.split(",")
			for s in selectedEvents:
				try:
					# Add selected event to temporary list to prevent the loop from being longer than intended
					if targetsNew not in targetEvents:
						targetsNew.append({"slug": eventSelectables[int(s) - 1]['slug'], "settings": target["settings"]})
				except ValueError:
					print(str(s) + " is not a number")
					pass
				except IndexError:
					print(str(s) + " is not an option")
					pass

	else:
		pass

for t in targetsRemove:
	targetEvents.remove(t)

targetEvents.extend(targetsNew)
if len(targetEvents) == 0:
	print("targets.txt is empty. Please add events to targets.txt or enter an event URL below: (leave blank to exit)")
	targetInput = input()
	if len(targetInput.strip()) == 0:
		exit()
	else:
		targetEvents.append({"slug": helper.gg_slug_cleaner(targetInput), "settings": mainSettings.copy()})
print(targetEvents)


for event in targetEvents:
	# ===================================== Query =====================================

	print_time()
	print("="*10 + " Starting queries")

	activeSettings = event["settings"]
	activeSlug = event["slug"]

	# Data about the event that doesn't change
	eventMainData = helper.gg_query(query=queryOnceData, variables={"eventSlug": activeSlug}, auth=authToken)['data']['event']

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
		"DQ count": {"Full": 0, "Losers": 0, "Winners": 0},
		"Prize info": ""
	}

	# Get brackets and keep only ones with 1 group
	phaseData = eventMainData['phases']
	phaseBrackets = []
	for phase in phaseData:
		if phase['groupCount'] == 1:
			phaseBrackets.append("[{0} {1}]".format(phase['phaseGroups']['nodes'][0]['bracketUrl'], phase['name']))

	# Get game ID
	eventMainInfo["Game ID"] = eventMainData['videogame']['id']

	# Get size of teams
	if eventMainData['teamRosterSize'] is not None:
		eventMainInfo["Team size"] = int(eventMainData['teamRosterSize']['maxPlayers'])

	# Determine query based on team size
	if eventMainInfo["Team size"] == 1:
		targetQuery = querySingles
	elif eventMainInfo["Team size"] == 2:
		targetQuery = queryDoubles
	else:
		print("Unsupported type")
		end_pause()
		continue

	# Initialize info about the event
	eventMainInfo["Tournament"] = eventMainData['tournament']['name']
	eventMainInfo["Event"] = eventMainData['name']
	eventMainInfo["URL"] = "https://www.start.gg/" + eventMainData['slug']
	eventMainInfo["Game"] = gameByID[eventMainData['videogame']['id']][0]
	eventMainInfo["Entrant count"] = eventMainData['numEntrants']
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
	pageCount = 1

	print("Settings:", activeSettings)
	# ===================================== Pages =====================================
	# Loop through pages until limit is reached
	while True:
		queryStartTime = time.time()

		eventStandingData = helper.event_data_slug(slug=activeSlug, page=pageCount, per_page=perPageCount, query=targetQuery, auth=authToken)
		eventStandingListTemp = eventStandingData['standings']['nodes']

		# If the returned page is empty, then there are no more pages to go through
		if len(eventStandingListTemp) == 0:
			print("\nNo more pages")
			break

		standingsList.extend(eventStandingListTemp)

		# Only placements up to a point are documented. Stop if too many
		if activeSettings["MaxPlacement"] > 0:
			if eventStandingListTemp[-1]['placement'] > activeSettings["MaxPlacement"]:
				print("\npages:", pageCount)
				break

		if (activeSettings["MaxPages"] > 0) and (activeSettings["MaxPages"] == pageCount):
			print("\nMax pages reached")
			break

		queryEndTime = time.time()

		totalPage = eventMainInfo["Entrant count"]/perPageCount
		currentPage = len(standingsList)/perPageCount
		print("\rPage: {c: <4} | Response time: {t} seconds | Entrants: {e: <7,}/{ec: <7,} | Est. remaining time: {remain} seconds"
			  .format(c=pageCount, t=queryEndTime - queryStartTime, e=len(standingsList), ec=eventMainInfo["Entrant count"],
					  remain=decreasingSleep.avg_time*(totalPage-currentPage)), end='', flush=True)

		pageCount += 1
		decreasingSleep.sleep(end_time=time.time())

	# ===================================== Tables =====================================
	print()
	print("="*10 + " Queries complete ")
	print_time()
	print("="*10 + " Creating table ")

	dqOrder = []
	tableString = ""

	# Team size = 1 || SINGLES
	if eventMainInfo["Team size"] == 1:
		tableString = """{|class="wikitable" style="text-align:center"\n!Place!!Name!!Character(s)!!Earnings\n"""
		rowString = """|-\n|{place}||{p1}||{heads}||\n"""
		for row in standingsList:
			placement = helper.make_ordinal(row['placement'])

			entrantID = row['entrant']['id']

			smasherName = row['entrant']['name'].split("|")[-1].strip()
			country = helper.get_flag(row)
			smasherString = helper.smasher_link(smasherName, country, row['placement'] <= activeSettings["MaxLinked"])

			charHeads = ""

			# DQ stuff
			setList = row['entrant']['paginatedSets']['nodes']

			dqJudgement, dqSets = helper.dq_judge(entrantID, setList, activeSettings["MaxDQ"])

			if dqJudgement == "pass":
				pass
			elif dqJudgement == "full":
				smasherString += " (DQ)"
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
				placement += "*" * (dqOrder.index(dqJudgement) + 1)

			# If the sets played are nothing but DQs, list characters as a dash
			if dqSets.count(0) == 0:
				charHeads = "&mdash;"

			# Append to table
			tableString += rowString.format(place=placement,
											p1=smasherString,
											heads=charHeads)

		tableString = tableString.replace("||||", "|| ||")

		tableString += "|}"

	# Team size = 2 || DOUBLES
	elif eventMainInfo["Team size"] == 2:
		tableString = """{|class="wikitable" style="text-align:center"\n!Place!!Name!!Character(s)!!Name!!Character(s)!!Earnings\n"""
		rowString = """|-\n|{place}||{p1}||{h1}||{p2}||{h2}||\n"""
		for row in standingsList:
			placement = helper.make_ordinal(row['placement'])

			entrantID = row['entrant']['id']

			teamMembers = row['entrant']['team']['members']
			smasherStrings = []
			charHeads = ""

			for i in range(2):
				sName = teamMembers[i]['participant']['gamerTag'].split("|")[-1].strip()
				sCountry = helper.get_flag(teamMembers[i]['participant'])
				sString = helper.smasher_link(sName, sCountry, row['placement'] <= activeSettings["MaxLinked"])

				smasherStrings.append(sString)

			# DQ stuff
			setList = row['entrant']['paginatedSets']['nodes']
			dqJudgement, dqSets = helper.dq_judge(entrantID, setList, activeSettings["MaxDQ"])

			if dqJudgement == "pass":
				pass
			elif dqJudgement == "full":
				for i in range(len(smasherStrings)):
					smasherStrings[i] += " (DQ)"
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
				placement += "*" * (dqOrder.index(dqJudgement) + 1)

			# If the sets played are nothing but DQs, list characters as a dash
			if dqSets.count(0) == 0:
				charHeads = "&mdash;"

			# Append to table
			tableString += rowString.format(place=placement,
											p1=smasherStrings[0],
											p2=smasherStrings[1],
											h1=charHeads, h2=charHeads)

		tableString = tableString.replace("||||", "|| ||")

		tableString += "|}"

	# Add asterisk notes to the end of the table
	if len(dqOrder) > 0:
		tableString += "\n"
		for d in dqOrder:
			tableString += "{{*}}" * (dqOrder.index(d) + 1) + "DQ'd in " + d.capitalize() + ".\n"

	# ===================================== Output =====================================
	print("="*10 + " Table complete ")
	print_time()

	headerString = "===''[[{0}]]'' {1}===\n"

	outputPath = os.path.join("outputs", str(activeSlug).replace("tournament/", "").replace("/event/", "/"))
	if not os.path.exists(outputPath):
		os.makedirs(outputPath)

	print("="*10 + " Writing to \"" + outputPath.replace("/", "\\") + "\\output.txt\" ")

	with open(os.path.join(outputPath, "output.txt"), "w+", encoding='utf-8') as f:
		# Header and Entrants
		if eventMainInfo["Team size"] == 1:
			f.write(headerString.format(gameByID[eventMainInfo["Game ID"]][0], "singles"))
			f.write("({0:,} entrants)<br>\n".format(eventMainInfo["Entrant count"]))
		elif eventMainInfo["Team size"] == 2:
			f.write(headerString.format(gameByID[eventMainInfo["Game ID"]][0], "doubles"))
			f.write("({0:,} teams)<br>\n".format(eventMainInfo["Entrant count"]))
		# Bracket(s)
		for i in range(len(phaseBrackets)):
			# The last bracket does not get a <br>
			if i != len(phaseBrackets) - 1:
				f.write(phaseBrackets[i] + "<br>\n")
			else:
				f.write(phaseBrackets[i] + "\n")
		# Table
		f.writelines(tableString)

	if activeSettings["OutputInfo"]:
		with open(os.path.join(outputPath, "info.txt"), "w+", encoding='utf-8') as f:
			json.dump(eventMainInfo, f, ensure_ascii=False, indent=1)

	print("\n"*2)


print("="*10 + " Finished ")
print_time()
end_pause()
