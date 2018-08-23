
import logging
import os

from phabricator import Phabricator


class PhabClient:

    _logger = logging.getLogger('PhabClient')

    def __init__(self):
        self._client = self._connect_phabricator(url=os.environ.get('NOTIPHIER_PHABRICATOR_URL'),
                                                 token=os.environ.get('NOTIPHIER_PHABRICATOR_TOKEN'))

    def _connect_phabricator(self, url, token):
        if not token:
            raise Exception("Can't find a token to connect to Phabricator.")

        if not url:
            raise Exception("Can't find Phabricator's URL.")

        try:
            return Phabricator(host=url, token=token)
        except Exception as e:
            self._logger.error("Error connecting to Phabricator: " + str(e))
            raise

    def get_users(self):
        self._logger.info("Getting list of users from Phabricator...")

        users = self._client.user.search()
        return { user['phid']: (user['fields']['username'], user['fields']['realName'])
                 for user in users.data
                 if 'disabled' not in user['fields']['roles'] and
                    'bot' not in user['fields']['roles'] and
                    user['phid'].startswith('PHID-USER')}
