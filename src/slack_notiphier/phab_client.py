
import json
import logging
import os
from termcolor import colored

from phabricator import Phabricator, APIError


class PhabClient:
    """
        Encapsulates all interaction with Phabricator.
    """

    _logger = logging.getLogger('PhabClient')

    def __init__(self):
        """
            Attempts to connect to Phabricator using the url and token supplied in slack Notiphier's config file.
            If a url or token is not found in the config file, they will be looked up in the environment variables:
                - NOTIPHIER_PHABRICATOR_URL
                - NOTIPHIER_PHABRICATOR_TOKEN
        """
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
        """
            Returns the list of human users from Phabricators.
            :return: {phid: (phab_username, phab_full_name)}
        """
        self._logger.info("Getting list of users from Phabricator...")

        users = self._client.user.search()
        return {user['phid']: (user['fields']['username'], user['fields']['realName'])
                for user in users.data
                if 'disabled' not in user['fields']['roles'] and
                   'bot' not in user['fields']['roles'] and
                   user['phid'].startswith('PHID-USER')}

    def get_transactions(self, object_type, object_phid, tx_phids):
        """
            Receives a list of Phabricator transactions and returns objects with only the relevant information, if any.
        """
        constraints = {'phids': tx_phids}

        try:
            txs = self._client.transaction.search(objectIdentifier=object_phid,
                                                  constraints=constraints)
        except APIError as e:
            # Swallow APIErrors related to unimplemented methods
            if "not implemented" in e.message:
                self._logger.error(colored("Unimplemented method in Phabricator: {}".format(e), 'red'))
                return []
            raise

        results = []
        for t in txs.data:
            self._logger.debug(colored("Transaction:\n{}".format(json.dumps(t, indent=4)), 'magenta'))

            # These types are as sent by Phabricator's Firehose Webhook
            if object_type == 'TASK':
                results.extend(self._handle_task(t))
            elif object_type == 'DREV':
                results.extend( self._handle_diff(t))
            elif object_type == 'PROJ':
                results.extend( self._handle_proj(t))
            elif object_type == 'REPO':
                results.extend( self._handle_repo(t))
            else:
                self._logger.debug(colored("No message will be generated for object of type {}".format(object_type),
                                           'red'))

        return results

    def _handle_task(self, task):
        """
            Receives an object representing a transaction for a task (in Phabricator's own format).
            Returns a generator with the relevant parts of the transactions.
        """
        if task['type'] == 'create':
            yield {
                'type': 'task-create',
                'author': task['authorPHID'],
                'task': task['objectPHID']
            }
        elif task['type'] == 'comment':
            for comment in task['comments']:
                if comment['removed']:
                    continue

                yield {
                    'type': 'task-create-comment',
                    'author': task['authorPHID'],
                    'task': task['objectPHID'],
                    'comment': comment['content']['raw']
                }
        elif task['type'] == 'owner':
            if task['authorPHID'] == task['fields']['new']:
                yield {
                    'type': 'task-claim',
                    'author': task['authorPHID'],
                    'task': task['objectPHID']
                }
            else:
                yield {
                    'type': 'task-assign',
                    'author': task['authorPHID'],
                    'task': task['objectPHID'],
                    'asignee': task['fields']['new']
                }
        elif task['type'] == 'status':
            yield {
                'type': 'task-change-status',
                'author': task['authorPHID'],
                'task': task['objectPHID'],
                'old': task['fields']['old'],
                'new': task['fields']['new']
            }
        elif task['type'] == 'priority':
            yield {
                'type': 'task-change-priority',
                'author': task['authorPHID'],
                'task': task['objectPHID'],
                'old': task['fields']['old']['name'],
                'new': task['fields']['new']['name']
            }
        else:
            self._logger.debug(colored("No message will be generated", 'red'))

    def _handle_diff(self, diff):
        """
            Receives an object representing a transaction for a differential revision (in Phabricator's own format).
            Returns a generator with the relevant parts of the transactions.
        """
        if diff['type'] == 'create':
            yield {
                'type': 'diff-create',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        elif diff['type'] == 'comment':
            for comment in diff['comments']:
                if comment['removed']:
                    continue

                yield {
                    'type': 'diff-create-comment',
                    'author': diff['authorPHID'],
                    'diff': diff['objectPHID'],
                    'comment': comment['content']['raw']
                }
        elif diff['type'] == 'update':
            yield {
                'type': 'diff-update',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        elif diff['type'] == 'abandon':
            yield {
                'type': 'diff-abandon',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        elif diff['type'] == 'reclaim':
            yield {
                'type': 'diff-reclaim',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        elif diff['type'] == 'accept':
            yield {
                'type': 'diff-accept',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        elif diff['type'] == 'request-changes':
            yield {
                'type': 'diff-request-changes',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        elif diff['type'] == 'commandeer':
            yield {
                'type': 'diff-commandeer',
                'author': diff['authorPHID'],
                'diff': diff['objectPHID']
            }
        else:
            self._logger.debug(colored("No message will be generated", 'red'))

    def _handle_proj(self, repo):
        """
            Receives an object representing a transaction for a project (in Phabricator's own format).
            Returns a generator with the relevant parts of the transactions.
        """
        if repo['type'] == 'create':
            yield {
                'type': 'proj-create',
                'author': repo['authorPHID'],
                'proj': repo['objectPHID']
            }
        else:
            self._logger.debug(colored("No message will be generated", 'red'))

    def _handle_repo(self, repo):
        """
            Receives an object representing a transaction for a repository (in Phabricator's own format).
            Returns a generator with the relevant parts of the transactions.
        """
        if repo['type'] == 'create':
            yield {
                'type': 'create-repo',
                'author': repo['authorPHID'],
                'repo': repo['objectPHID']
            }
        else:
            self._logger.debug(colored("No message will be generated", 'red'))
