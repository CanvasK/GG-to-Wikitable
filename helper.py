import math
import urllib.request
import urllib.parse
import urllib.error
import json
import time


def gg_query(query, variables, auth, json_err=0):
	"""

	:type query: str
	:param query: The query for the start.gg API
	:type variables: dict
	:param variables: The changeable settings for the API such as page number, items per page, etc.
	:type auth: str
	:param auth: The user's start.gg authorization code
	:param json_err: DO NOT USE. Used for error handling
	:return:
	:rtype: dict
	"""
	header = {"Authorization": "Bearer " + auth, "Content-Type": "application/json"}

	if json_err >= 5:
		print("The start.gg servers aren't sending valid JSON after several attempts. Try a different query or wait a few minutes.")
		time.sleep(30)
		exit()

	json_request = {'query': query, 'variables': variables}
	req = urllib.request.Request('https://api.smash.gg/gql/alpha', data=json.dumps(json_request).encode('utf-8'), headers=header)
	try:
		response = urllib.request.urlopen(req)
		if response.getcode() == 200:
			pass
		elif response.getcode() == 429:  # too many requests
			print("Too many requests. Temporarily throttling")
			time.sleep(20)
			pass
		elif response.getcode() == 503:  # service unavailable
			pass
	except urllib.error.HTTPError as e:
		print(e)
		print("Service unavailable, sleeping for a bit")
		time.sleep(5)
		try:
			response = urllib.request.urlopen(req)
		except urllib.error.HTTPError as e:
			print(e)
			print("Service unavailable, sleeping for a bit")
			time.sleep(10)
			try:
				response = urllib.request.urlopen(req)
			except urllib.error.HTTPError as e:
				print(e)
				print("Service unavailable, sleeping for a bit")
				time.sleep(20)
				response = urllib.request.urlopen(req)

	res = response.read()
	response.close()

	try:
		return json.loads(res)
	except json.decoder.JSONDecodeError as e:
		print("Received invalid JSON from server. Trying again in a bit.")
		print(e)
		time.sleep(1*(json_err+1))
		return gg_query(query=query, variables=variables, auth=auth, json_err=json_err+1)


def event_data_slug(slug, page, query, auth):
	variables = {"eventSlug": slug, "page": page}
	response = gg_query(query=query, variables=variables, auth=auth)
	try:
		data = response['data']['event']
		return data
	except KeyError:
		print(response)


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
with open("country short.tsv", 'r', encoding='utf-8') as f:
	for line in f:
		(key, value) = line.split("\t")
		countryShort[key.strip()] = value.strip()


def get_flag(stnd: dict):
	c = ""
	if stnd['player']['user'] is not None:
		if stnd['player']['user']['location'] is not None:
			if stnd['player']['user']['location']['country'] is not None:
				c = stnd['player']['user']['location']['country']

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


class Sleeper:
	"""
	This class provides a sleep function that gradually shortens in length.
	For use when sending APIs that have limits on the number of queries they allow within a time period,
	but when the queries take long enough that static delays waste time.

	:argument:
		start_time (float) and end_time (float): Simple time.time() will do. These can be the same when initializing.
	"""
	def __init__(self, start_time, end_time):
		self.start_time = start_time
		self.end_time = end_time
	sleep_time = 0.5
	delta_time = 1
	avg_time = 1
	list_times = []

	def sleep(self, end_time: float):
		"""Sleeps and adjusts sleep duration based on the average of the previous 5 calls.
		:param end_time: time.time(). Should ideally be used after a query
		"""
		self.end_time = end_time
		self.delta_time = min(5, self.end_time - self.start_time)
		self.start_time = time.time()
		self.list_times.append(self.delta_time)
		del self.list_times[:-5]
		self.avg_time = sum(self.list_times)/len(self.list_times)

		# start.gg limits requests to 80 per 60 seconds, or about 0.75 seconds per request
		# Sleep is soft capped at 0.8 to allow for some buffer
		# If 0.8 is exceeded, sleep duration is slowly increased to get back in line
		if self.avg_time >= 2.0:
			self.sleep_time = max(0.0, self.sleep_time - 0.1)
		elif self.avg_time >= 1.0:
			self.sleep_time = max(0.0, self.sleep_time - 0.02)
		elif self.avg_time > 0.8:
			self.sleep_time = max(0.0, self.sleep_time - 0.01)
		else:
			self.sleep_time = self.sleep_time + 0.015

		# print("|{0:.4f} (avg {1})".format(self.sleep_time, self.avg_time))
		time.sleep(self.sleep_time)
