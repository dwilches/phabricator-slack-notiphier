
import json
import logging
from termcolor import colored

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

        # Tasks
        if transaction['type'] == 'task-create':
            return "User {} created task {}".format(transaction['author'],
                                                    transaction['task'])
        elif transaction['type'] == 'task-create-comment':
            return "User {} commented on task {} with {}".format(transaction['author'],
                                                                 transaction['task'],
                                                                 transaction['comment'])
        elif transaction['type'] == 'task-claim':
            return "User {} claimed task {}".format(transaction['author'],
                                                    transaction['task'])
        elif transaction['type'] == 'task-assign':
            return "User {} assigned {} to task {}".format(transaction['author'],
                                                           transaction['asignee'],
                                                           transaction['task'])
        elif transaction['type'] == 'task-change-status':
            return "User {} changed the status of task {} from {} to {}".format(transaction['author'],
                                                                                transaction['task'],
                                                                                transaction['old'],
                                                                                transaction['new'])
        elif transaction['type'] == 'task-change-priority':
            return "User {} changed the priority of task {} from {} to {}".format(transaction['author'],
                                                                                  transaction['task'],
                                                                                  transaction['old'],
                                                                                  transaction['new'])

        # Differential Revisions
        elif transaction['type'] == 'diff-create':
            return "User {} created diff {}".format(transaction['author'],
                                                    transaction['diff'])
        elif transaction['type'] == 'diff-create-comment':
            return "User {} commented on diff {} with {}".format(transaction['author'],
                                                                 transaction['diff'],
                                                                 transaction['comment'])
        elif transaction['type'] == 'diff-update':
            return "User {} updated diff {}".format(transaction['author'],
                                                    transaction['diff'])
        elif transaction['type'] == 'diff-abandon':
            return "User {} abandoned diff {}".format(transaction['author'],
                                                      transaction['diff'])
        elif transaction['type'] == 'diff-reclaim':
            return "User {} reclaimed diff {}".format(transaction['author'],
                                                      transaction['diff'])
        elif transaction['type'] == 'diff-accept':
            return "User {} accepted diff {}".format(transaction['author'],
                                                     transaction['diff'])
        elif transaction['type'] == 'diff-request-changes':
            return "User {} requested changes to diff {}".format(transaction['author'],
                                                                 transaction['diff'])
        elif transaction['type'] == 'diff-commandeer':
            return "User {} took command of diff {}".format(transaction['author'],
                                                            transaction['diff'])

        # Projects
        elif transaction['type'] == 'proj-create':
            return "User {} created project {}".format(transaction['author'],
                                                       transaction['proj'])

        # Repositories
        elif transaction['type'] == 'repo-create':
            return "User {} created repo {}".format(transaction['author'],
                                                    transaction['repo'])
