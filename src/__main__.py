
from flask import Flask, request, abort, make_response, jsonify

from . import webhook_firehose

app = Flask(__name__)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/', methods=['GET'])
def hello():
    return 'Hello, World!'


@app.route('/firehose', methods=['POST'])
def phab_webhook_firehose():
    if not request.json:
        abort(400)

    #webhook_firehose()

    return "OK\n"


if __name__ == '__main__':
    app.run(debug=True)

