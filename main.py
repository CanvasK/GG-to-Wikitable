import helper
import math
import re
import configparser
import time

print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))

config = configparser.ConfigParser()
config.read('config.cfg')

with open("auth.txt") as a:
	authToken = a.read().strip()

slugURL = config['request']['EventSlug']
if "start.gg" in slugURL:
	slugURL = re.findall(r"start\.gg/(.*)", slugURL)[0]

header = {"Authorization": "Bearer " + authToken, "Content-Type": "application/json"}

gameByID = {1:     ['Super Smash Bros. Melee', 'SSBM'],
			2:     ['Project M', 'PM'],
			3:     ['Super Smash Bros. for Wii U', 'SSB4'],
			4:     ['Super Smash Bros.', 'SSB'],
			29:    ['Super Smash Bros. for Nintendo 3DS', 'SSB4'],
			1386:  ['Super Smash Bros. Ultimate', 'SSBU'],
			33602: ['Project+', 'P+'],
			39478: ['Smash Remix', 'Remix']}


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
		standings(query: {page: $page, perPage: 50}) {
			nodes {
				placement
				entrant {
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

eventType = config.get('request', 'EventType').lower()
targetQuery = ""
if eventType == "singles":
	targetQuery = querySingles
elif eventType == "doubles":
	targetQuery = queryDoubles
else:
	print("Invalid type")
	time.sleep(config.getint('other', 'EndPause'))
	exit()


# ===================================== Query =====================================
print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
print("="*10 + " Starting queries")


# Data about the event that doesn't change
eventData = helper.event_data_slug(slugURL, 1, queryOnceData, header)
phaseData = eventData['phases']
phaseBrackets = []
for p in phaseData:
	if p['groupCount'] == 1:
		phaseBrackets.append("[{0} {1}]".format(p['phaseGroups']['nodes'][0]['bracketUrl'], p['name']))

# Get game ID
gameID = eventData['videogame']['id']
if eventType == "singles":
	totalPages = math.ceil(eventData['numEntrants'] / 50)
elif eventType == "doubles":
	totalPages = math.ceil(eventData['numEntrants'] / 50)
else:
	print("Invalid type")
	totalPages = math.ceil(eventData['numEntrants'] / 50)
	exit()

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
print("pages:", totalPages)
print("roster size:", rosterSize)
print(time.strftime("%Y-%m-%d %H:%M:%S+00:00 (UTC)", time.gmtime(int(eventData['startAt']))))
print("online:", eventData['isOnline'])
print("prize info:", eventData['prizingInfo'])
print()

standingsList = list()

# Loop through pages until limit is reached
for p in range(1, totalPages+1):
	eventStandingData = helper.event_data_slug(slugURL, p, targetQuery, header)
	eventStandingListTemp = eventStandingData['standings']['nodes']

	# If the returned page is empty, then there are no more pages to go through
	if len(eventStandingListTemp) == 0:
		print("\nNo more pages:", p)
		break

	standingsList.extend(eventStandingListTemp)

	# Only placements up to a point are documented. Stop if too many
	if maxPlace > 0:
		if eventStandingListTemp[-1]['placement'] > maxPlace:
			print("\npages:", p)
			break

	if (maxPages > 0) and (maxPages == p):
		print("\nMax pages reached")
		break

	print("\rCurrent page: " + str(p), end='', flush=True)
	time.sleep(60/80)  # Limit for calls is 80 per 60 seconds

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
		playerID = row['entrant']['id']

		smasherName = row['entrant']['name'].split("|")[-1].strip()
		country = helper.parse_flag(row)
		smasherString = helper.smasher_link(smasherName, country, row['placement'] <= maxLink)
		placement = helper.make_ordinal(row['placement'])
		charHeads = ""

		# DQ stuff
		setList = row['entrant']['paginatedSets']['nodes']
		dqSets = []
		dqBracket = None
		for sL in setList:
			# If the resulting score is a DQ and the winner is not the target player
			# API does not say who received the DQ score, so a winner check is needed
			if sL['displayScore'] == "DQ" and sL['winnerId'] != playerID:
				dqSets.append(sL['round'])

				# Sets are ordered with most recent set played first
				# Only note the most recent DQ and ignore the rest
				if dqBracket is None:
					if sL['round'] < 0:
						dqBracket = "losers"
					else:
						dqBracket = "winners"
			else:
				dqSets.append(None)

		if len(dqSets) - maxDq == dqSets.count(None):
			smasherString += " (DQ)"

		# Mark placement with an asterisk if they received a DQ
		# Keep track of when a "losers DQ" or "winners DQ" happens
		if dqBracket is not None:
			if dqBracket == "losers":
				if dqBracket not in dqOrder:
					dqOrder.append(dqBracket)
			if dqBracket == "winners":
				if dqBracket not in dqOrder:
					dqOrder.append(dqBracket)
			if not smasherString.endswith(" (DQ)"):
				placement += "*" * (dqOrder.index(dqBracket) + 1)

		# If the sets played are nothing but DQs, list characters as a dash
		if dqSets.count(None) == 0:
			charHeads = "&mdash;"

		# Append to table
		tableString += rowString.format(place=placement,
										p1=smasherString,
										heads=charHeads)

	tableString = tableString.replace("||||", "|| ||")

	tableString += "|}"
	# Add asterisk notes to the end of the table
	if len(dqOrder) > 0:
		tableString += "\n"
		for d in dqOrder:
			tableString += "{{*}}" * (dqOrder.index(d) + 1) + "DQ'd in " + d.capitalize() + ".\n"

# Team size = 2 || DOUBLES
elif rosterSize == 2:
	tableString = """{|class="wikitable" style="text-align:center"\n!Place!!Name!!Character(s)!!Name!!Character(s)!!Earnings\n"""
	rowString = """|-\n|{place}||{p1}|| ||{p2}|| ||\n"""
	for row in standingsList:
		teamMembers = row['entrant']['team']['members']
		smasherStrings = []

		for i in range(2):
			sName = teamMembers[i]['participant']['gamerTag'].split("|")[-1].strip()
			sCountry = helper.parse_flag(teamMembers[i]['participant'])
			sString = helper.smasher_link(sName, sCountry, row['placement'] <= maxLink)

			smasherStrings.append(sString)
		# # Teammate 1
		# smasherName1 = teamMembers[0]['participant']['gamerTag'].split("|")[-1].strip()
		# country1 = parse_flag(teamMembers[0]['participant'])
		# smasherString1 = smasher_link(smasherName1, country1, row['placement'] <= maxLink)
		#
		# # Teammate 2
		# smasherName2 = teamMembers[1]['participant']['gamerTag'].split("|")[-1].strip()
		# country2 = parse_flag(teamMembers[1]['participant'])
		# smasherString2 = smasher_link(smasherName2, country2, row['placement'] <= maxLink)

		# Append to table
		tableString += rowString.format(place=helper.make_ordinal(row['placement']),
										p1=smasherStrings[0],
										p2=smasherStrings[1])

	tableString = tableString.replace("||||", "|| ||") + "|}\n"

else:
	print("FORMAT NOT SUPPORTED")
	time.sleep(config.getint('other', 'EndPause'))
	exit()

# ===================================== Output =====================================
print("="*10 + " Table complete ")
print(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
print("="*10 + " Writing to output.txt ")

headerString = "===''[[{0}]]'' {1}===\n"

with open("output.txt", "w+", encoding='utf-8') as f:
	# Header
	f.write(headerString.format(gameByID[gameID][0], eventType))
	# Entrants
	f.write("({0:,} entrants)<br>\n".format(eventData['numEntrants']))
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
