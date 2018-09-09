
import hashlib
import hmac

from flask import Flask, request, abort, make_response, jsonify

from .webhook_firehose import WebhookFirehose
from .config import get_config
from .logger import Logger


app = Flask(__name__)
handler = WebhookFirehose()

_hmac = get_config('phabricator_webhook_hmac').encode()
_logger = Logger('Main')


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/firehose', methods=['POST'])
def phab_webhook_firehose():
    expected_digest = request.headers.get('X-Phabricator-Webhook-Signature', None)
    if not expected_digest:
        _logger.warn("Incoming request didn't contain a message signature")
        abort(400)

    actual_digest = hmac.new(_hmac, request.data, hashlib.sha256).hexdigest()

    if expected_digest != actual_digest:
        _logger.warn("Incoming request contained an invalid message signature")
        abort(400)

    if not request.json:
        abort(400)

    handler.handle(request.json)

    return "OK\n"


@app.route('/health')
def health():
    return "OK\n"


if __name__ == '__main__':
    app.run(use_reloader=False,
            debug=get_config('_flask_debug', False),
            host=get_config('host', '0.0.0.0'),
            port=get_config('port', 5000))
