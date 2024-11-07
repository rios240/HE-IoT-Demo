# Rate limiters for use in Flask routes

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from http import HTTPStatus


# set up a default rate limiter
limiter = Limiter(key_func=get_remote_address,   # limiting by remote address
                  default_limits=["5/minute", "200/day"],
                  headers_enabled=True)


# Test if a authentication failure response
def is_unauthorized(response):
    return response.status_code == HTTPStatus.UNAUTHORIZED or response.status_code == HTTPStatus.FORBIDDEN


# set up a rate limiter to be shared by /bulb/* routes
bulb_route_limit = limiter.shared_limit("200/day;50/hour", scope="bulb_route")

# set up a rate limiter to be shared by /user/* routes
user_route_limit = limiter.shared_limit("200/day;50/hour", scope="user_route")

# set up a rate limiter to be used for failed authentication attempts from same IP address
auth_limit = limiter.shared_limit("5/minute;25/day", scope="auth", deduct_when=is_unauthorized)



