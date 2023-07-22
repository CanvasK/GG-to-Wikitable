import helper
import os
import re
import configparser
import time

print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))

config = configparser.ConfigParser()
config.read('config.cfg')

try:
	with open("auth.txt") as a:
		authToken = a.read().strip()
		if len(authToken) == 0:
			print("auth.txt is empty. Please paste your authentication token into the file and save")
			time.sleep(20)
			exit()
except FileNotFoundError:
	print("auth.txt does not exist. Please create the file in the same folder as main.py with an authentication token")
	time.sleep(20)
	exit()


header = {"Authorization": "Bearer " + authToken, "Content-Type": "application/json"}

gameByID = {1:     ['Super Smash Bros. Melee', 'SSBM'],
			2:     ['Project M', 'PM'],
			3:     ['Super Smash Bros. for Wii U', 'SSB4'],
			4:     ['Super Smash Bros.', 'SSB'],
			29:    ['Super Smash Bros. for Nintendo 3DS', 'SSB4'],
			1386:  ['Super Smash Bros. Ultimate', 'SSBU'],
			33602: ['Project+', 'P+'],
			39478: ['Smash Remix', 'SR']}


queryOnceData = """
	query ($eventSlug: String!){
		event(slug: $eventSlug) {
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
			# standings (query: {page: 1, perPage: 100}) { pageInfo { totalPages } }
			phases {
				name
				groupCount
				phaseGroups(query: {perPage: 50, page: 1}) {
					nodes { bracketUrl }
				}
			}
		}
	}
"""

querySingles = """
query ($eventSlug: String!, $page: Int!){
	event(slug: $eventSlug) {
		standings(query: {page: $page, perPage: 50}) {
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
					paginatedSets(page: 1, perPage: 50, sortType: RECENT) {
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
query ($eventSlug: String!, $page: Int!){
	event(slug: $eventSlug) {
		standings(query: {page: $page, perPage: 40}) {
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
					paginatedSets(page: 1, perPage: 50, sortType: RECENT) {
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

# ===================================== Config =====================================
maxPlace = config.getint('request', 'MaxPlacement')
maxPages = config.getint('request', 'MaxPages')


# ===================================== Query =====================================
print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
print("="*10 + " Starting queries")

operationMode = config.get('request', 'Mode').lower()
targets = []

if operationMode == "single":
	slugURL = config.get('request', 'EventSlug').strip()
	if len(slugURL) == 0:
		print("EventSlug is empty. Make sure you are using the correct Mode in the config or add an event to EventSlug")
		time.sleep(20)
		exit()

	if "start.gg" in slugURL:
		slugURL = re.findall(r"start\.gg/(.*)", slugURL)[0]

	eventType = config.get('request', 'EventType').lower()
	targets.append({"slug": slugURL, "type": eventType})

elif operationMode == "bulk":
	with open("bulk.txt", 'r', encoding='utf-8') as b:
		for line in b:
			if not line.startswith("#"):
				if len(line) > 0:
					spl = line.split(",")
					targets.append({"slug": spl[0].strip(), "type": spl[1].strip()})
	if len(targets) == 0:
		print("bulk.txt is empty. Make sure you are using the correct Mode in the config or add events to bulk.txt")
		time.sleep(20)
		exit()

else:
	print("Invalid Mode. Either check the spelling or add a mode")
	time.sleep(20)
	exit()

for tar in targets:
	# eventType = config.get('request', 'EventType').lower()
	targetQuery = ""
	if tar['type'] == "singles":
		targetQuery = querySingles
	elif tar['type'] == "doubles":
		targetQuery = queryDoubles
	else:
		print("Invalid type")
		time.sleep(config.getint('other', 'EndPause'))
		exit()

	# Data about the event that doesn't change
	eventData = helper.event_data_slug(tar['slug'], 1, queryOnceData, header)
	phaseData = eventData['phases']
	phaseBrackets = []
	for phase in phaseData:
		if phase['groupCount'] == 1:
			phaseBrackets.append("[{0} {1}]".format(phase['phaseGroups']['nodes'][0]['bracketUrl'], phase['name']))

	# Get game ID
	gameID = eventData['videogame']['id']

	# Get size of teams
	if eventData['teamRosterSize'] is not None:
		rosterSize = int(eventData['teamRosterSize']['maxPlayers'])
	else:
		rosterSize = 1

	print(eventData['tournament']['name'])
	print(eventData['name'])
	print("https://www.start.gg/" + eventData['slug'])
	print("game:", gameByID[eventData['videogame']['id']][0])
	print("entrants:", eventData['numEntrants'])
	# print("pages:", totalPages)
	print("roster size:", rosterSize)
	print(time.strftime("%Y-%m-%d %H:%M:%S+00:00 (UTC)", time.gmtime(int(eventData['startAt']))))
	print("online:", eventData['isOnline'])
	print("prize info:", eventData['prizingInfo'])
	print()

	standingsList = list()
	pageCount = 1

	queryStartTime = time.time()
	queryEndTime = time.time()

	decreasingSleep = helper.Sleeper(start_time=time.time(), end_time=time.time())
	# Loop through pages until limit is reached
	while True:
		queryStartTime = time.time()

		eventStandingData = helper.event_data_slug(tar['slug'], pageCount, targetQuery, header)
		eventStandingListTemp = eventStandingData['standings']['nodes']

		# If the returned page is empty, then there are no more pages to go through
		if len(eventStandingListTemp) == 0:
			print("\nNo more pages:", pageCount)
			break

		standingsList.extend(eventStandingListTemp)

		# Only placements up to a point are documented. Stop if too many
		if maxPlace > 0:
			if eventStandingListTemp[-1]['placement'] > maxPlace:
				print("\npages:", pageCount)
				break

		if (maxPages > 0) and (maxPages == pageCount):
			print("\nMax pages reached")
			break

		queryEndTime = time.time()
		print("\rCurrent page: {c: <4} ({t} seconds) [entrants: {e: <7,}/{ec: <7,}]".format(c=pageCount, t=queryEndTime - queryStartTime,
																				e=len(standingsList), ec=eventData['numEntrants']),
			  end='', flush=True)
		pageCount += 1
		decreasingSleep.sleep(end_time=time.time())

	# ===================================== Tables =====================================
	print()
	print("="*10 + " Queries complete ")
	print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
	print("="*10 + " Creating table ")

	maxLink = config.getint('output', 'MaxLinked')
	maxDq = config.getint('output', 'MaxDQ')
	dqOrder = []
	tableString = ""

	# Team size = 1 || SINGLES
	if rosterSize == 1:
		tableString = """{|class="wikitable" style="text-align:center"\n!Place!!Name!!Character(s)!!Earnings\n"""
		rowString = """|-\n|{place}||{p1}||{heads}||\n"""
		for row in standingsList:
			placement = helper.make_ordinal(row['placement'])

			entrantID = row['entrant']['id']

			smasherName = row['entrant']['name'].split("|")[-1].strip()
			country = helper.get_flag(row)
			smasherString = helper.smasher_link(smasherName, country, row['placement'] <= maxLink)

			charHeads = ""

			# DQ stuff
			setList = row['entrant']['paginatedSets']['nodes']

			dqJudgement, dqSets = helper.dq_judge(entrantID, setList, maxDq)

			if dqJudgement == "pass":
				pass
			elif dqJudgement == "full":
				smasherString += " (DQ)"
			else:
				if dqJudgement == "losers":
					if dqJudgement not in dqOrder:
						dqOrder.append(dqJudgement)
				if dqJudgement == "winners":
					if dqJudgement not in dqOrder:
						dqOrder.append(dqJudgement)
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
	elif rosterSize == 2:
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
				sString = helper.smasher_link(sName, sCountry, row['placement'] <= maxLink)

				smasherStrings.append(sString)

			# DQ stuff
			setList = row['entrant']['paginatedSets']['nodes']
			dqJudgement, dqSets = helper.dq_judge(entrantID, setList, maxDq)

			if dqJudgement == "pass":
				pass
			elif dqJudgement == "full":
				for i in range(len(smasherStrings)):
					smasherStrings[i] += " (DQ)"
			else:
				if dqJudgement == "losers":
					if dqJudgement not in dqOrder:
						dqOrder.append(dqJudgement)
				if dqJudgement == "winners":
					if dqJudgement not in dqOrder:
						dqOrder.append(dqJudgement)
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

	else:
		print("FORMAT NOT SUPPORTED")
		time.sleep(config.getint('other', 'EndPause'))
		exit()

	# Add asterisk notes to the end of the table
	if len(dqOrder) > 0:
		tableString += "\n"
		for d in dqOrder:
			tableString += "{{*}}" * (dqOrder.index(d) + 1) + "DQ'd in " + d.capitalize() + ".\n"

	# ===================================== Output =====================================
	print("="*10 + " Table complete ")
	print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))

	outputPath = os.path.join("outputs", tar['slug'])
	if not os.path.exists(outputPath):
		os.makedirs(outputPath)

	print("="*10 + " Writing to \"" + outputPath.replace("/", "\\") + "\\output.txt\" ")

	headerString = "===''[[{0}]]'' {1}===\n"

	with open(os.path.join(outputPath, "output.txt"), "w+", encoding='utf-8') as f:
		# Header
		f.write(headerString.format(gameByID[gameID][0], tar['type']))
		# Entrants
		if tar['type'] == "singles":
			f.write("({0:,} entrants)<br>\n".format(eventData['numEntrants']))
		if tar['type'] == "doubles":
			f.write("({0:,} teams)<br>\n".format(eventData['numEntrants']))
	# Bracket(s)
		for i in range(len(phaseBrackets)):
			# The last bracket does not get a <br>
			if i != len(phaseBrackets) - 1:
				f.write(phaseBrackets[i] + "<br>\n")
			else:
				f.write(phaseBrackets[i] + "\n")
		# Table
		f.writelines(tableString)

	print("="*10 + " Finished ")
	print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
	time.sleep(config.getint('other', 'EndPause'))
