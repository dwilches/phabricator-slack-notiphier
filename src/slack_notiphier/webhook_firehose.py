
from .phab_client import PhabClient
from .slack_client import SlackClient


class WebhookFirehose:

    def __init__(self):
        self._slack_client = SlackClient()
        self._phab_client = PhabClient()

    def handle(self, request):
        #object_type = request['object']['type']
        object_phid = request['object']['phid']

        transactions = self.get_transactions(object_phid, request['transactions'])
        message = self._handle_transactions(transactions)

        self._slack_client.send_message(message)

    def get_transactions(self, object_phid, wrapped_phids):
        phids = [t['phid'] for t in wrapped_phids]
        return self._phab_client.get_transactions(object_phid, phids)

    def _handle_transactions(self, transactions):
        return [ self._handle_transaction(t) for t in transactions]

    def _handle_transaction(self, transaction):
        if transaction['type'] == 'create-task':
            return "User {} created task {}".format(transaction['author'],
                                                    transaction['task'])
        elif transaction['type'] == 'create-comment':
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
