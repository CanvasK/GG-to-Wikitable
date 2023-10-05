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

def base_gg_query(query, variables, auth, auto_retry=True, retry_delay=10, retry_attempts=4):
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
	:type retry_attempts: int
	:param retry_attempts: Number of retries
	:return:
	:rtype: dict
	"""

	def err_print(err, err_response):
		print()
		print(err)
		print(err_response)

	def sleep_print(s):
		_s = s
		while _s >= 0:
			print(f"\r{_s}...", end='')
			time.sleep(1)
			_s = _s - 1
		print()

	def _gg_query(query, variables, auth, auto_retry, retry_delay, retry_attempts):
		header = {"Authorization": "Bearer " + auth, "Content-Type": "application/json"}
		json_request = {'query': query, 'variables': variables}

		try:
			if retry_attempts == 0:
				raise TooManyRetriesError

			req = urllib.request.Request('https://api.smash.gg/gql/alpha', data=json.dumps(json_request).encode('utf-8'), headers=header)
			response = urllib.request.urlopen(req, timeout=300)
			if response.getcode() == 400:
				raise BadRequestError
			elif response.getcode() == 429:  # too many requests
				raise TooManyRequestsError
			elif response.getcode() == 503:  # service unavailable
				raise ServiceUnavailableError
			elif response.getcode() == 504:  # Gateway time-out
				raise GatewayTimeOutError

			res = response.read()
			response.close()
			try:
				return json.loads(res)
			except json.decoder.JSONDecodeError as e:
				err_print(e, "Received invalid JSON from server, trying again in {} seconds".format(retry_delay))
				time.sleep(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2, retry_attempts - 1)

		except TooManyRetriesError as e:
			err_print(e, "The query has failed too many times. Try again later or try a different query")
			return

		except BadRequestError as e:
			err_print(e, "400: Bad request. Good chance the authorization key isn't valid")
			return

		except TooManyRequestsError as e:
			if auto_retry:
				err_print(e, "429: Too many requests right now, trying again in {} seconds".format(retry_delay))
				sleep_print(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2, retry_attempts - 1)
			else:
				err_print(e, "429: Too many requests right now")
				return

		except ServiceUnavailableError as e:
			if auto_retry:
				err_print(e, "503: start.gg servers are trash, trying again in {} seconds".format(retry_delay))
				sleep_print(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2, retry_attempts - 1)
			else:
				err_print(e, "503: start.gg servers are trash")
				return

		except GatewayTimeOutError as e:
			if auto_retry:
				err_print(e, "504: start.gg servers timed out, trying again in {} seconds".format(retry_delay))
				sleep_print(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2, retry_attempts - 1)
			else:
				err_print(e, "504: start.gg servers timed out")
				return

		except urllib.error.HTTPError as e:
			if auto_retry:
				err_print(e, "Service unavailable, trying again in {} seconds".format(retry_delay))
				sleep_print(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2, retry_attempts - 1)
			else:
				err_print(e, "Service unavailable")
				return

		except urllib.error.URLError as e:
			if auto_retry:
				err_print(e, "Couldn't connect, trying again in {} seconds".format(retry_delay))
				sleep_print(retry_delay)
				return _gg_query(query, variables, auth, auto_retry, retry_delay * 2, retry_attempts - 1)
			else:
				err_print(e, "Couldn't connect")
				return

	return _gg_query(query=query, variables=variables, auth=auth, auto_retry=auto_retry, retry_delay=retry_delay, retry_attempts=retry_attempts)


def event_data_slug(slug, page, per_page, query, auth):
	variables = {"eventSlug": slug, "page": page, "perPage": per_page}
	response = base_gg_query(query=query, variables=variables, auth=auth)
	try:
		data = response['data']['event']
		return data
	except KeyError:
		print(response)
	except TypeError:
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


def smasher_link(name, flag="", disambig="", enable_link=True):
	"""
	Helper function to create links to Smasher pages
	:param name: Smasher's name
	:type name: str
	:param disambig: Specifier if more than one Smasher has the same name. The "p=" in the {{Sm}} template
	:type disambig: str
	:param flag: The flag to display
	:type flag: str
	:type enable_link: bool
	:return: str
	"""
	if enable_link:
		sm_str = "{{Sm|" + name + "}}"
		if disambig != "":
			sm_str = sm_str.replace("}}", "|p=" + disambig + "}}")
		if flag != "":
			sm_str = sm_str.replace("}}", "|"+flag+"}}")
	else:
		if flag != "":
			sm_str = "{{Flag|"+flag+"}} "+name
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
