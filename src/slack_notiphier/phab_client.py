
import json
import os
from urllib.parse import urljoin

from phabricator import Phabricator, APIError

from .logger import Logger


class PhabClient:
    """
        Encapsulates all interaction with Phabricator.
    """

    _logger = Logger('PhabClient')

    def __init__(self):
        """
            Attempts to connect to Phabricator using the url and token supplied in slack Notiphier's config file.
            If a url or token is not found in the config file, they will be looked up in the environment variables:
                - NOTIPHIER_PHABRICATOR_URL
                - NOTIPHIER_PHABRICATOR_TOKEN
        """
        self._url = os.environ.get('NOTIPHIER_PHABRICATOR_URL')
        self._client = self._connect_phabricator(token=os.environ.get('NOTIPHIER_PHABRICATOR_TOKEN'))

    def _connect_phabricator(self, token):
        url = urljoin(self._url, "api/")

        if not token:
            raise Exception("Can't find a token to connect to Phabricator.")

        if not url:
            raise Exception("Can't find Phabricator's URL.")

        try:
            client = Phabricator(host=url, token=token)
            # If the RUL is invalid, this health check should find it out
            client.conduit.ping()
            return client
        except Exception as e:
            self._logger.error("Error connecting to Phabricator. Is the url '{}' valid?: {}", url, e)
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
                self._logger.error("Unimplemented method in Phabricator: {}", e)
                return []
            raise

        results = []
        for t in txs.data:
            self._logger.debug("Transaction:\n{}", json.dumps(t, indent=4))

            # These types are as sent by Phabricator's Firehose Webhook
            if object_type == 'TASK':
                results.extend(self._handle_task(t))
            elif object_type == 'DREV':
                results.extend(self._handle_diff(t))
            elif object_type == 'PROJ':
                results.extend(self._handle_proj(t))
            elif object_type == 'REPO':
                results.extend(self._handle_repo(t))
            else:
                self._logger.debug("No message will be generated for object of type {}", object_type)

        return results

    def get_link(self, phid):
        """
            Returns a link to a task, differential revision, project or repo given its PHID.
            The link is returned in a format suitable for Slack.
        """
        if phid.startswith("PHID-TASK-"):
            task = self._client.maniphest.search(constraints={'phids': [phid]})
            task_id = task['data'][0]['id']
            task_name = task['data'][0]['fields']['name']
            return "<{}/T{}|T{}>: {}".format(self._url, task_id, task_id, task_name)

        if phid.startswith("PHID-DREV-"):
            task = self._client.differential.revision.search(constraints={'phids': [phid]})
            diff_id = task['data'][0]['id']
            diff_name = task['data'][0]['fields']['title']
            return "<{}/D{}|D{}>: {}".format(self._url, diff_id, diff_id, diff_name)

        if phid.startswith("PHID-PROJ-"):
            task = self._client.differential.project.search(constraints={'phids': [phid]})
            proj_id = task['data'][0]['id']
            proj_name = task['data'][0]['fields']['name']
            return "<{}/project/view/{}|{}>".format(self._url, proj_id, proj_name)

        if phid.startswith("PHID-REPO-"):
            task = self._client.diffusion.repository.search(constraints={'phids': [phid]})
            proj_id = task['data'][0]['id']
            proj_name = task['data'][0]['fields']['name']
            return "<{}/source/{}|{}>".format(self._url, proj_id, proj_name)

        return None

    def get_owner(self, phid):
        """
            If given a task's PHID, returns the PHID of its owner. If given a differential revision's PHID,
            it returns its author's PHID.
        """
        if phid.startswith("PHID-TASK-"):
            task = self._client.maniphest.search(constraints={'phids': [phid]})
            return task['data'][0]['fields']['ownerPHID']

        if phid.startswith("PHID-DREV-"):
            task = self._client.differential.revision.search(constraints={'phids': [phid]})
            return task['data'][0]['fields']['authorPHID']

        return None

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
            self._logger.debug("No message will be generated")

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
            self._logger.debug("No message will be generated")

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
            self._logger.debug("No message will be generated")

    def _handle_repo(self, repo):
        """
            Receives an object representing a transaction for a repository (in Phabricator's own format).
            Returns a generator with the relevant parts of the transactions.
        """
        if repo['type'] == 'create':
            yield {
                'type': 'repo-create',
                'author': repo['authorPHID'],
                'repo': repo['objectPHID']
            }
        else:
            self._logger.debug("No message will be generated")
