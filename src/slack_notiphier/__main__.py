
from flask import Flask, request, abort, make_response, jsonify

from .webhook_firehose import WebhookFirehose


app = Flask(__name__)
handler = WebhookFirehose()


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/firehose', methods=['POST'])
def phab_webhook_firehose():
    if not request.json:
        abort(400)

    handler.handle(request.json)

    return "OK\n"


@app.route('/health')
def health():
    return "OK\n"


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0')
