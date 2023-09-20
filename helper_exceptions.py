class TooManyRequestsError(Exception):
	# Too many requests at a time
	pass


class ServiceUnavailableError(Exception):
	# Couldn't connect
	pass


class BadRequestError(Exception):
	# Bad request, likely auth code
	pass


class SlugMissingError(Exception):
	# slug is missing error
	pass
