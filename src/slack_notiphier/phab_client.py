
import json
import logging
import os
from termcolor import colored

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

    def get_transactions(self, object_phid, tx_phids):
        constraints = {'phids': tx_phids}
        txs = self._client.transaction.search(objectIdentifier=object_phid,
                                              constraints=constraints)

        results = []
        for t in txs.data:
            self._logger.debug(colored("Transaction:\n{}".format(json.dumps(t, indent=4)), 'magenta'))

            if self._is_task(object_phid) and t['type'] == 'create':
                results.append({
                    'type': 'create-task',
                    'author': t['authorPHID'],
                    'task': t['objectPHID']
                })
            elif self._is_task(object_phid) and t['type'] == 'comment':
                for comment in t['comments']:
                    if comment['removed']:
                        continue

                    results.append({
                        'type': 'create-comment-task',
                        'author': t['authorPHID'],
                        'task': t['objectPHID'],
                        'comment': comment['content']['raw']
                    })
            elif self._is_task(object_phid) and t['type'] == 'owner':
                if t['authorPHID'] == t['fields']['new']:
                    results.append({
                        'type': 'claim-task',
                        'author': t['authorPHID'],
                        'task': t['objectPHID']
                    })
                else:
                    results.append({
                        'type': 'assign-task',
                        'author': t['authorPHID'],
                        'task': t['objectPHID'],
                        'asignee': t['fields']['new']
                    })
            elif self._is_task(object_phid) and t['type'] == 'status':
                results.append({
                    'type': 'change-status-task',
                    'author': t['authorPHID'],
                    'task': t['objectPHID'],
                    'old': t['fields']['old'],
                    'new': t['fields']['new']
                })
            else:
                self._logger.debug(colored("No message will be generated"))

        return results

    def _is_task(self, phid):
        return phid.startswith('PHID-TASK-')
