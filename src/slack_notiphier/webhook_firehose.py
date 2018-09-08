
import json

from .users import Users
from .logger import Logger
from .phab_client import PhabClient
from .slack_client import SlackClient


class WebhookFirehose:
    """
        Receives notifications coming from a Phabricator Firehose Webhook.
        It then converts each notification to a human-readable message and sends it through Slack.
    """
    _logger = Logger('WebhookFirehose')

    def __init__(self):
        self._slack_client = SlackClient()
        self._phab_client = PhabClient()
        self._users = Users(phab_client=self._phab_client,
                            slack_client=self._slack_client)

        message = "Slack Notiphier started running."
        self._logger.info(message)
        self._slack_client.send_message(message)

    def handle(self, request):
        """
            Handle a single request from one of Phabricator's Firehose webhooks.
            It extracts the relevant data and sends the message to Slack.
        """
        object_type = request['object']['type']
        object_phid = request['object']['phid']

        #self._logger.debug("Incoming message:\n{}", json.dumps(request, indent=4))

        transactions = self._get_transactions(object_type, object_phid, request['transactions'])
        self._handle_transactions(object_type, transactions)

    def _get_transactions(self, object_type, object_phid, wrapped_phids):
        """
            Receives a list of transactions as received by the Firehose, and returns a list with only the interesting
            parts of the transactions.
        """
        phids = [t['phid'] for t in wrapped_phids]
        return self._phab_client.get_transactions(object_type, object_phid, phids)

    def _handle_transactions(self, object_type, transactions):
        """
            Receives a list of interesting transactions and sends messages to Slack.
        """
        for t in transactions:
            message = self._handle_transaction(object_type, t)

            if message:
                self._slack_client.send_message(message)
                self._logger.debug("Message: {}", message)

    def _handle_transaction(self, object_type, transaction):
        """
            Receives a single interesting transaction and send a message to Slack.
        """

        if object_type == "TASK":
            return self._handle_task(transaction)

        if object_type == "DREV":
            return self._handle_diff(transaction)

        if object_type == "PROJ":
            return self._handle_proj(transaction)

        if object_type == "REPO":
            return self._handle_repo(transaction)

        self._logger.warn("No message will be generated for: {}", json.dumps(transaction, indent=4))

    def _handle_task(self, transaction):
        """
            Receives an internal transaction object and returns a message ready for Slack.
        """

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

        self._logger.warn("No message will be generated for: {}", json.dumps(transaction, indent=4))

    def _handle_diff(self, transaction):
        """
            Receives an internal transaction object and returns a message ready for Slack.
        """

        diff_link = self._phab_client.get_link(transaction['diff'])

        owner_phid = self._phab_client.get_owner(transaction['diff'])
        author_phid = transaction['author']

        if not self._users[owner_phid]:
            raise ValueError("Unknown Phabricator user: {}".format(owner_phid))
        if not self._users[author_phid]:
            raise ValueError("Unknown Phabricator user: {}".format(author_phid))

        owner_name = self._users[owner_phid]['phab_username']
        owner_mention = self._users.get_mention(owner_phid)
        author_name = self._users[author_phid]['phab_username']

        if transaction['type'] == 'diff-create':
            return "User {} created diff {}".format(author_name,
                                                    diff_link)

        elif transaction['type'] == 'diff-create-comment':
            message = "User {} commented on diff {} with {}".format(author_name,
                                                                    diff_link,
                                                                    transaction['comment'])
            return "{} {}".format(owner_mention, message) if author_name != owner_name else message

        elif transaction['type'] == 'diff-update':
            return "User {} updated diff {}".format(author_name,
                                                    diff_link)

        elif transaction['type'] == 'diff-abandon':
            return "User {} abandoned diff {}".format(author_name,
                                                      diff_link)

        elif transaction['type'] == 'diff-reclaim':
            return "User {} reclaimed diff {}".format(author_name,
                                                      diff_link)

        elif transaction['type'] == 'diff-accept':
            return "{} User {} accepted diff {}".format(owner_mention,
                                                        author_name,
                                                        diff_link)

        elif transaction['type'] == 'diff-request-changes':
            return "{} User {} requested changes to diff {}".format(owner_mention,
                                                                    author_name,
                                                                    diff_link)

        elif transaction['type'] == 'diff-commandeer':
            return "{} User {} took command of diff {}".format(owner_mention,
                                                               author_name,
                                                               diff_link)

        self._logger.warn("No message will be generated for: {}", json.dumps(transaction, indent=4))

    def _handle_proj(self, transaction):
        """
            Receives an internal transaction object and returns a message ready for Slack.
        """

        proj_link = self._phab_client.get_link(transaction['proj'])

        author_phid = transaction['author']
        author_name = self._users[author_phid]['phab_username']

        if transaction['type'] == 'proj-create':
            return "User {} created project {}".format(author_name,
                                                       proj_link)

        self._logger.warn("No message will be generated for: {}", json.dumps(transaction, indent=4))

    def _handle_repo(self, transaction):
        """
            Receives an internal transaction object and returns a message ready for Slack.
        """

        repo_link = self._phab_client.get_link(transaction['repo'])

        author_phid = transaction['author']
        author_name = self._users[author_phid]['phab_username']

        if transaction['type'] == 'repo-create':
            return "User {} created repository {}".format(author_name,
                                                          repo_link)

        self._logger.warn("No message will be generated for: {}", json.dumps(transaction, indent=4))
