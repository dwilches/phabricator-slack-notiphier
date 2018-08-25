
import json
import logging
from termcolor import colored

from .users import Users

from .phab_client import PhabClient
from .slack_client import SlackClient


class WebhookFirehose:
    """
        Receives notifications coming from a Phabricator Firehose Webhook.
        It then converts each notification to a human-readable message and sends it through Slack.
    """
    _logger = logging.getLogger('WebhookFirehose')

    def __init__(self):
        self._slack_client = SlackClient()
        self._phab_client = PhabClient()
        self._users = Users(phab_client=self._phab_client,
                            slack_client=self._slack_client)

        message = "Slack Notiphier started running."
        self._logger.info(colored(message, 'green'))
        self._slack_client.send_message(message)

    def handle(self, request):
        """
            Handle a single request from one of Phabricator's Firehose webhooks.
            It extracts the relevant data and sends the message to Slack.
        """
        object_type = request['object']['type']
        object_phid = request['object']['phid']

        self._logger.debug(colored("Incoming message:\n{}".format(json.dumps(request, indent=4)), 'green'))

        transactions = self._get_transactions(object_type, object_phid, request['transactions'])
        self._handle_transactions(transactions)

    def _get_transactions(self, object_type, object_phid, wrapped_phids):
        """
            Receives a list of transactions as received by the Firehose, and returns a list with only the interesting
            parts of the transactions.
        """
        phids = [t['phid'] for t in wrapped_phids]
        return self._phab_client.get_transactions(object_type, object_phid, phids)

    def _handle_transactions(self, transactions):
        """
            Receives a list of interesting transactions and sends messages to Slack.
        """
        for t in transactions:
            message = self._handle_transaction(t)
            self._slack_client.send_message(message)
            self._logger.debug(colored("Message: {}".format(message), 'red', attrs=['bold']))

    def _handle_transaction(self, transaction):
        """
            Receives a single interesting transaction and send a message to Slack.
        """

        if transaction['type'].startswith("task-"):
            return self._handle_task(transaction)

        #TODO: remove
        author = self._users.get_mention(transaction['author']) if 'author' in transaction else None

        # Differential Revisions
        if transaction['type'] == 'diff-create':
            return "User {} created diff {}".format(author,
                                                    transaction['diff'])
        elif transaction['type'] == 'diff-create-comment':
            return "User {} commented on diff {} with {}".format(author,
                                                                 transaction['diff'],
                                                                 transaction['comment'])
        elif transaction['type'] == 'diff-update':
            return "User {} updated diff {}".format(author,
                                                    transaction['diff'])
        elif transaction['type'] == 'diff-abandon':
            return "User {} abandoned diff {}".format(author,
                                                      transaction['diff'])
        elif transaction['type'] == 'diff-reclaim':
            return "User {} reclaimed diff {}".format(author,
                                                      transaction['diff'])
        elif transaction['type'] == 'diff-accept':
            return "User {} accepted diff {}".format(author,
                                                     transaction['diff'])
        elif transaction['type'] == 'diff-request-changes':
            return "User {} requested changes to diff {}".format(author,
                                                                 transaction['diff'])
        elif transaction['type'] == 'diff-commandeer':
            return "User {} took command of diff {}".format(author,
                                                            transaction['diff'])

        # Projects
        elif transaction['type'] == 'proj-create':
            return "User {} created project {}".format(author,
                                                       transaction['proj'])

        # Repositories
        elif transaction['type'] == 'repo-create':
            return "User {} created repo {}".format(author,
                                                    transaction['repo'])

    def _handle_task(self, transaction):

        task_link = self._phab_client.get_link(transaction['task'])

        owner_phid = self._phab_client.get_owner(transaction['task'])
        owner_name = self._users[owner_phid]['phab_username']
        owner_mention = self._users.get_mention(owner_phid)

        author_phid = transaction['author']
        author_name = self._users[author_phid]['phab_username']

        if transaction['type'] == 'task-create':
            return "User {} created task {}".format(author_name,
                                                    task_link)
        elif transaction['type'] == 'task-create-comment':
            message = "User {} commented on task {} with: {}".format(author_name,
                                                                     task_link,
                                                                     transaction['comment'])

            return "{} {}".format(owner_mention, message) if author_name != owner_name else message

        elif transaction['type'] == 'task-claim':
            return "User {} claimed task {}".format(author_name,
                                                    task_link)

        elif transaction['type'] == 'task-assign':
            if transaction['asignee']:
                asignee_mention = self._users.get_mention(transaction['asignee'])
            else:
                asignee_mention = "nobody"

            return "User {} assigned {} to task {}".format(author_name,
                                                           asignee_mention,
                                                           task_link)

        elif transaction['type'] == 'task-change-status':
            message = "User {} changed the status of task {} from {} to {}".format(author_name,
                                                                                   task_link,
                                                                                   transaction['old'],
                                                                                   transaction['new'])
            return "{} {}".format(owner_mention, message) if author_name != owner_name else message

        elif transaction['type'] == 'task-change-priority':
            message = "User {} changed the priority of task {} from {} to {}".format(author_name,
                                                                                     task_link,
                                                                                     transaction['old'],
                                                                                     transaction['new'])
            return "{} {}".format(owner_mention, message) if author_name != owner_name else message
