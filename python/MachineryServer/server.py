# Server frontend with
#  (a) a rate-limited REST API for bulb commands
#  (b) session based authentication
#  Expects Sqlite3 database named smartbulb.sqlite

from flask import Flask, jsonify
from limiter import limiter
from http import HTTPStatus
import errors
from blueprints.root.root_bp import root_bp

server = Flask(__name__)     # the frontend Flask app

limiter.init_app(server)     # register Flask app with limiters

# register blueprints
server.register_blueprint(root_bp, url_prefix="/")

# secret key for sessions (32 random bytes)
server.secret_key = b'\xbe\x10\x87\xeb\x45\x8c\x8c\xde'\
                       b'\xa9\xe2\xc9\x2c\x73\x9f\x51\x7e'\
                       b'\xa8\xf2\x07\x13\x2e\x4d\x4d\x7a'\
                       b'\xae\x13\xe9\xf2\x08\x2f\xc7\x6d'


@server.errorhandler(errors.InvalidUsage)
# Flask handler to return error messages
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status.value

    # if response.status_code == HTTPStatus.UNAUTHORIZED:
    #     response.headers["WWW-Authenticate"] = "Basic realm:'Restricted Area'"

    return response


@server.errorhandler(HTTPStatus.TOO_MANY_REQUESTS.value)
# Flask handler for 429 (rate limit) error
#  This is an exception handler; do not raise another exception
def handle_rate_limit(e):
    err = errors.InvalidUsage("API limit exceeded (" + e.description + ")", HTTPStatus.TOO_MANY_REQUESTS)
    return handle_invalid_usage(err)


@server.after_request
# Flask handler to run before sending a response
def handle_after_request(response):
    # block pages from loading if reflected XSS attacks are detected
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # do not store in cache (hits performance!)
    response.headers["Cache-Control"] = "no-store"
    # resources can only be loaded from same origin (no inline JavaScript)
    # response.headers["Content-Security-Policy"] = "default-src 'self'"
    # must use HTTPS for the next 1 year, including for all subdomains
    response.headers["Strict-Transport-Security"] = "max-age:31536000; includeSubDomains"
    # do not try to guess content type
    response.headers["X-Content-Type-Options"] = "nosniff"
    # iframes can only have content from same origin server
    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    return response
