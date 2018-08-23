
import logging
import os

from slackclient import SlackClient as Slack


class SlackClient:

    _logger = logging.getLogger('SlackClient')

    def __init__(self):
        self._client = self._connect_slack(os.environ.get('NOTIPHIER_SLACK_TOKEN'))

    def _connect_slack(self, token):
        if not token:
            raise Exception("Can't find a token to connect to Slack.")

        try:
            return Slack(token)
        except Exception as e:
            self._logger.error("Error connecting to Slack: " + str(e))
            raise

    def get_users(self):
        """
            Requires this permission in Slack:
                View the workspace's list of members and their contact information
                users:read
        """
        self._logger.info("Getting list of users from Slack...")

        response = self._client.api_call("users.list")
        if not response['ok']:
            raise Exception("Couldn't retrieve user list from Slack. Error: " + str(response['error']))

        return { user['real_name']: user['id'] for user in response['members']
                 if not user.get('is_bot', True) and user.get('real_name') }

    def send_message(self, message):
        print(message)