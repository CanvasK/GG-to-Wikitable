from helper_exceptions import *

import math
import os
import urllib.request
import urllib.parse
import urllib.error
import json
import time
import re


# Query related stuff

def base_gg_query(query, variables, auth, auto_retry=True, retry_delay=10):
	"""

	:type query: str
	:param query: The query for the start.gg API
	:type variables: dict
	:param variables: The changeable settings for the API such as page number, items per page, etc.
	:type auth: str
	:param auth: The user's start.gg authorization code
	:type auto_retry: bool
	:param auto_retry: If the query should be run again if an error occurs
	:type retry_delay: int
	:param retry_delay: Time between auto retries
	:return:
	:rtype: dict
	"""

	def _gg_query(query, variables, auth, auto_retry, retry_delay):
		header = {"Authorization": "Bearer " + auth, "Content-Type": "application/json"}
		json_request = {'query': query, 'variables': variables}

		def err_prnt(err, err_response):
			print()
			print(err)
			print(err_response)

		try:
			req = urllib.request.Request('https://api.smash.gg/gql/alpha', data=json.dumps(json_request).encode('utf-8'), headers=header)
			response = urllib.request.urlopen(req, timeout=20)
			if response.getcode() == 400:
				raise BadRequestError
			elif response.getcode() == 429:  # too many requests
				raise TooManyRequestsError
			elif response.getcode() == 503:  # service unavailable
				raise ServiceUnavailableError

			res = response.read()
			response.close()
			try:
				return json.loads(res)
			except json.decoder.JSONDecodeError as e:
				err_prnt(e, "Received invalid JSON from server, trying again in {} seconds".format(retry_delay))
				time.sleep(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2)

		except BadRequestError as e:
			err_prnt(e, "400: Bad request. Good chance the authorization key isn't valid")
			return

		except TooManyRequestsError as e:
			if auto_retry:
				err_prnt(e, "429: Too many requests right now, trying again in {} seconds".format(retry_delay))
				time.sleep(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2)
			else:
				err_prnt(e, "429: Too many requests right now")
				return

		except ServiceUnavailableError as e:
			if auto_retry:
				err_prnt(e, "503: start.gg servers are trash, trying again in {} seconds".format(retry_delay))
				time.sleep(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2)
			else:
				err_prnt(e, "503: start.gg servers are trash")
				return

		except urllib.error.HTTPError as e:
			if auto_retry:
				err_prnt(e, "Service unavailable, trying again in {} seconds".format(retry_delay))
				time.sleep(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2)
			else:
				err_prnt(e, "Service unavailable")
				return

		except urllib.error.URLError as e:
			if auto_retry:
				err_prnt(e, "Couldn't connect, trying again in {} seconds".format(retry_delay))
				time.sleep(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2)
			else:
				err_prnt(e, "Couldn't connect")
				return

	return _gg_query(query=query, variables=variables, auth=auth, auto_retry=auto_retry, retry_delay=retry_delay)


def event_data_slug(slug, page, per_page, query, auth):
	variables = {"eventSlug": slug, "page": page, "perPage": per_page}
	response = base_gg_query(query=query, variables=variables, auth=auth)
	try:
		data = response['data']['event']
		return data
	except KeyError:
		print(response)


# Slug related stuff

def gg_slug_cleaner(slug):
	if len(slug) == 0:
		raise SlugMissingError

	# Slug shouldn't contain the domain
	if "start.gg" in slug:
		slug = re.findall(r"start\.gg/(.*)", slug)[0].strip()

	# API does not consider "events == event" despite it working in browser
	slug = slug.replace("/events/", "/event/")
	# Remove stuff at the end
	# Slug should only be "tournament/T/event/E" at most
	if "/event/" in slug:
		slug = slug.split("/", 4)[0:4]
	else:
		slug = slug.split("/", 4)[0:2]
	slug = "/".join(slug)

	return slug


# Extra functions
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


countryShort = {}
with open(os.path.join(os.path.dirname(__file__), "country short.tsv"), 'r', encoding='utf-8') as f:
	for line in f:
		(key, value) = line.split("\t")
		countryShort[key.strip()] = value.strip()


def get_flag(standing_data: dict):
	"""
	Gets the user's flag. Does a bunch of checks because there are several things that can be None
	:param standing_data: Data from the query result starting where 'GamerTag' is present
	:return: str
	"""
	c = ""
	if standing_data['user'] is not None:
		if standing_data['user']['location'] is not None:
			if standing_data['user']['location']['country'] is not None:
				c = standing_data['user']['location']['country']

	if c in countryShort:
		c = countryShort[c]
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


def dq_judge(e_id, sets: dict, max_dq):
	_dqSets = []
	_dqLatest = None
	_judgement = "pass"
	for s in sets:
		# If the resulting score is a DQ and the winner is not the target player.
		# API does not say who received the DQ score, so a winner check is needed
		if s['displayScore'] == "DQ" and s['winnerId'] != e_id:
			# The specific round doesn't matter, only -/+
			# - = losers, + = winners
			_dqSets.append(math.copysign(1, s['round']))

			# Sets are ordered with the first index being the last set
			# Only most recent, therefore lowest index, is necessary
			if _dqLatest is None:
				_dqLatest = math.copysign(1, s['round'])
		else:
			# Round number should never be 0, can be used as a null value instead
			_dqSets.append(0)

	# if ((len(_dqSets) - max_dq) >= _dqSets.count(0)) or _dqSets.count(0) == 0:
	if (len(_dqSets) - _dqSets.count(0) >= max_dq) or _dqSets.count(0) == 0:
		_judgement = "full"
	else:
		if _dqLatest == -1:
			_judgement = "losers"
		elif _dqLatest == 1:
			_judgement = "winners"
		else:
			_judgement = "pass"

	return _judgement, _dqSets
