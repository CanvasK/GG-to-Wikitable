import urllib.request
import urllib.parse
import urllib.error
import json
import time


def gg_query(query, variables, headers):
	json_request = {'query': query, 'variables': variables}
	req = urllib.request.Request('https://api.smash.gg/gql/alpha', data=json.dumps(json_request).encode('utf-8'), headers=headers)
	try:
		response = urllib.request.urlopen(req)
	except urllib.error.HTTPError:
		print("Service unavailable, sleeping for a bit")
		time.sleep(5)
		try:
			response = urllib.request.urlopen(req)
		except urllib.error.HTTPError:
			print("Service unavailable, sleeping for a bit")
			time.sleep(10)
			try:
				response = urllib.request.urlopen(req)
			except urllib.error.HTTPError:
				print("Service unavailable, sleeping for a bit")
				time.sleep(20)
				response = urllib.request.urlopen(req)

	return json.loads(response.read())


def make_ordinal(n):
	"""
	Convert an integer into its ordinal representation::

		make_ordinal(0)   => '0th'
		make_ordinal(3)   => '3rd'
		make_ordinal(122) => '122nd'
		make_ordinal(213) => '213th'
	Copied from https://stackoverflow.com/a/50992575
	"""
	n = int(n)
	if 11 <= (n % 100) <= 13:
		suffix = 'th'
	else:
		suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
	return str(n) + suffix


def parse_flag(stnd: dict):
	c = ""
	shorthand = {
		"United States": "USA",
		"United Kingdom": "UK",
		"United Arab Emirates": "UAE"
	}
	if stnd['player']['user'] is not None:
		if stnd['player']['user']['location'] is not None:
			if stnd['player']['user']['location']['country'] is not None:
				c = stnd['player']['user']['location']['country']

	if c in shorthand:
		c = shorthand[c]
	return c


def smasher_link(name, flag="", link=True):
	"""
	:type name: str
	:type flag: str
	:type link: bool
	:return: str
	"""
	if link:
		if flag != "":
			sm_str = "{{Sm|" + name + "|" + flag + "}}"
		else:
			sm_str = "{{Sm|" + name + "}}"
	else:
		if flag != "":
			sm_str = "{{Flag|" + flag + "}} " + name
		else:
			sm_str = name

	return sm_str


def event_data_slug(slug, page, query, headers):
	variables = {"eventSlug": slug, "page": page}
	try:
		response = gg_query(query, variables, headers)
	except json.decoder.JSONDecodeError as e:
		print(e)
		time.sleep(0.8)
		response = gg_query(query, variables, headers)
	try:
		data = response['data']['event']
		return data
	except KeyError:
		print(response)
