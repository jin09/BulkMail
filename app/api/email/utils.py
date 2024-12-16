from fastapi import Request


def get_request_id(request: Request) -> str:
    """
    Get the request ID from the provided request object.

    This function retrieves the `request_id` attribute from the state object of the
    given request. If no such attribute is present, it returns a default value of
    "default_request_id".

    :param request: The incoming request object containing state attributes.
    :type request: Request
    :return: The request ID if available, otherwise a default value.
    :rtype: str
    """
    return getattr(request.state, "request_id", "default_request_id")
