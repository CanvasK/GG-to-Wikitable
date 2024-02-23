class TooManyRequestsError(Exception):
	# Too many requests at a time
	pass


class ServiceUnavailableError(Exception):
	# Couldn't connect
	pass


class GatewayTimeOutError(Exception):
	# start.gg's servers timed-out
	pass


class BadRequestError(Exception):
	# Bad request, likely auth code
	pass


class SlugMissingError(Exception):
	# slug is missing error
	pass


class TooManyRetriesError(Exception):
	# Too many fails
	pass


class QueryTooComplexError(Exception):
	# Query complexity exceeds 1_000. Likely needs smaller PerPage
	pass
