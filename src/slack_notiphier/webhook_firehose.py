
import json
import logging
from termcolor import colored

from .phab_client import PhabClient
from .slack_client import SlackClient


class WebhookFirehose:

    _logger = logging.getLogger('SlackClient')

    def __init__(self):
        self._slack_client = SlackClient()
        self._phab_client = PhabClient()

    def handle(self, request):
        #object_type = request['object']['type']
        object_phid = request['object']['phid']

        self._logger.debug(colored("Incoming message:\n{}".format(json.dumps(request, indent=4)), 'green'))

        transactions = self.get_transactions(object_phid, request['transactions'])
        self._handle_transactions(transactions)

    def get_transactions(self, object_phid, wrapped_phids):
        phids = [t['phid'] for t in wrapped_phids]
        return self._phab_client.get_transactions(object_phid, phids)

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
