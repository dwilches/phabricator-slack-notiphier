
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
        object_type = request['object']['type']
        object_phid = request['object']['phid']

        self._logger.debug(colored("Incoming message:\n{}".format(json.dumps(request, indent=4)), 'green'))

        transactions = self._get_transactions(object_type, object_phid, request['transactions'])
        self._handle_transactions(transactions)

    def _get_transactions(self, object_type, object_phid, wrapped_phids):
        phids = [t['phid'] for t in wrapped_phids]
        return self._phab_client.get_transactions(object_type, object_phid, phids)

    def _handle_transactions(self, transactions):
        for t in transactions:
            message = self._handle_transaction(t)
            self._slack_client.send_message(message)
            self._logger.debug(colored("Message: {}".format(message), 'red', attrs=['bold']))

    def _handle_transaction(self, transaction):
        if transaction['type'] == 'create-task':
            return "User {} created task {}".format(transaction['author'],
                                                    transaction['task'])
        elif transaction['type'] == 'create-comment-task':
            return "User {} commented on task {} with {}".format(transaction['author'],
                                                                 transaction['task'],
                                                                 transaction['comment'])
        elif transaction['type'] == 'claim-task':
            return "User {} claimed task {}".format(transaction['author'],
                                                    transaction['task'])
        elif transaction['type'] == 'assign-task':
            return "User {} assigned {} to task {}".format(transaction['author'],
                                                           transaction['asignee'],
                                                           transaction['task'])
        elif transaction['type'] == 'change-status-task':
            return "User {} changed the status of task {} from {} to {}".format(transaction['author'],
                                                                                transaction['task'],
                                                                                transaction['old'],
                                                                                transaction['new'])
        elif transaction['type'] == 'change-priority-task':
            return "User {} changed the priority of task {} from {} to {}".format(transaction['author'],
                                                                                  transaction['task'],
                                                                                  transaction['old'],
                                                                                  transaction['new'])
        elif transaction['type'] == 'create-repo':
            return "User {} created repo {}".format(transaction['author'],
                                                    transaction['repo'])
        elif transaction['type'] == 'create-diff':
            return "User {} created diff {}".format(transaction['author'],
                                                    transaction['diff'])
        elif transaction['type'] == 'create-comment-diff':
            return "User {} commented on diff {} with {}".format(transaction['author'],
                                                                 transaction['diff'],
                                                                 transaction['comment'])
        elif transaction['type'] == 'update-diff':
            return "User {} updated diff {}".format(transaction['author'],
                                                    transaction['diff'])
        elif transaction['type'] == 'abandon-diff':
            return "User {} abandoned diff {}".format(transaction['author'],
                                                      transaction['diff'])
        elif transaction['type'] == 'reclaim-diff':
            return "User {} reclaimed diff {}".format(transaction['author'],
                                                      transaction['diff'])
        elif transaction['type'] == 'accept-diff':
            return "User {} accepted diff {}".format(transaction['author'],
                                                     transaction['diff'])
        elif transaction['type'] == 'request-changes-diff':
            return "User {} requested changes to diff {}".format(transaction['author'],
                                                                 transaction['diff'])
        elif transaction['type'] == 'commandeer-diff':
            return "User {} took command of diff {}".format(transaction['author'],
                                                            transaction['diff'])
        elif transaction['type'] == 'create-proj':
            return "User {} created project {}".format(transaction['author'],
                                                       transaction['proj'])
