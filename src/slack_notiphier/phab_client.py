
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

            if self._is_task(object_phid):
                results.extend(self._handle_task(t))
            elif self._is_diff(object_phid):
                results.extend( self._handle_diff(t))
            elif self._is_repo(object_phid):
                results.extend( self._handle_repo(t))
            else:
                self._logger.debug(colored("No message will be generated", 'red'))

        return results

    def _handle_task(self, task):
        if task['type'] == 'create':
            yield {
                'type': 'create-task',
                'author': task['authorPHID'],
                'task': task['objectPHID']
            }
        elif task['type'] == 'comment':
            for comment in task['comments']:
                if comment['removed']:
                    continue

                yield {
                    'type': 'create-comment-task',
                    'author': task['authorPHID'],
                    'task': task['objectPHID'],
                    'comment': comment['content']['raw']
                }
        elif task['type'] == 'owner':
            if task['authorPHID'] == task['fields']['new']:
                yield {
                    'type': 'claim-task',
                    'author': task['authorPHID'],
                    'task': task['objectPHID']
                }
            else:
                yield {
                    'type': 'assign-task',
                    'author': task['authorPHID'],
                    'task': task['objectPHID'],
                    'asignee': task['fields']['new']
                }
        elif task['type'] == 'status':
            yield {
                'type': 'change-status-task',
                'author': task['authorPHID'],
                'task': task['objectPHID'],
                'old': task['fields']['old'],
                'new': task['fields']['new']
            }
        else:
            self._logger.debug(colored("No message will be generated", 'red'))

    def _handle_repo(self, repo):
        if repo['type'] == 'create':
            yield {
                'type': 'create-repo',
                'author': repo['authorPHID'],
                'repo': repo['objectPHID']
            }
        else:
            self._logger.debug(colored("No message will be generated", 'red'))

    def _handle_diff(self, diff):
        if diff['type'] == 'create':
            yield {
                'type': 'create-diff',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        elif diff['type'] == 'comment':
            for comment in diff['comments']:
                if comment['removed']:
                    continue

                yield {
                    'type': 'create-comment-diff',
                    'author': diff['authorPHID'],
                    'diff': diff['objectPHID'],
                    'comment': comment['content']['raw']
                }
        elif diff['type'] == 'abandon':
            yield {
                'type': 'abandon-diff',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        else:
            self._logger.debug(colored("No message will be generated", 'red'))

    def _is_task(self, phid):
        return phid.startswith('PHID-TASK-')

    def _is_diff(self, phid):
        return phid.startswith('PHID-DREV-')

    def _is_repo(self, phid):
        return phid.startswith('PHID-REPO-')
