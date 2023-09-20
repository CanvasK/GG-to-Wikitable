import time


class Sleeper:
	"""
	This class provides a sleep function that gradually shortens in length.
	For use when sending APIs that have limits on the number of queries they allow within a time period,
	but when the queries take long enough that static delays waste time.

	:argument:
		start_time (float) and end_time (float): Simple time.time() will do. These can be the same when initializing.
	"""
	def __init__(self, start_time, end_time, target_delay=0.8, list_size=10):
		self.start_time = start_time
		self.end_time = end_time
		self.target_delay = target_delay
		self.list_size = list_size

	sleep_time = 0.5
	delta_time = 1
	avg_time = 1
	list_times = []

	def sleep(self, end_time: float):
		"""
		Sleeps and adjusts sleep duration based on the average of the previous 5 calls.
		:param end_time: time.time(). Should ideally be used after a query
		"""
		self.end_time = end_time
		self.delta_time = min(5, self.end_time - self.start_time)
		self.start_time = time.time()
		self.list_times.append(self.delta_time)
		del self.list_times[:-self.list_size]
		self.avg_time = sum(self.list_times)/len(self.list_times)

		# start.gg limits requests to 80 per 60 seconds, or about 0.75 seconds per request
		# If target_delay is exceeded, sleep duration is slowly increased to get back in line
		if self.avg_time >= self.target_delay*2.5:
			self.sleep_time = max(0.0, self.sleep_time - 0.1)
		elif self.avg_time >= self.target_delay*1.25:
			self.sleep_time = max(0.0, self.sleep_time - 0.02)
		elif self.avg_time > self.target_delay:
			self.sleep_time = max(0.0, self.sleep_time - 0.01)
		else:
			self.sleep_time = self.sleep_time + 0.015

		# print("|{0:.4f} (avg {1})".format(self.sleep_time, self.avg_time))
		time.sleep(self.sleep_time)
