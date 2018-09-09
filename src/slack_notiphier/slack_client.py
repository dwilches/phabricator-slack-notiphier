
import os

import slackclient

from .logger import Logger
from .config import get_config


class SlackClient:
    """
        Encapsulates all interaction with Slack.
    """

    _logger = Logger('SlackClient')

    def __init__(self):
        self._client = self._connect_slack(get_config('slack_token'))
        self._channel = get_config('slack_default_channel')

    def _connect_slack(self, token):
        if not token:
            raise Exception("Can't find a token to connect to Slack.")

        try:
            return slackclient.SlackClient(token)
        except Exception as e:
            self._logger.error("Error connecting to Slack: ", e)
            raise

    def get_users(self):
        """
            Requires this permission in Slack:
                View the workspace's list of members and their contact information
                users:read

            Returns: {real_name: slack_user_id}
        """
        self._logger.info("Getting list of users from Slack...")

        response = self._client.api_call("users.list")
        if not response['ok']:
            raise Exception("Couldn't retrieve user list from Slack. Error: " + str(response['error']))

        return {user['real_name']: user['id'] for user in response['members']
                if not user.get('is_bot', True)
                and not user.get('deleted', True)
                and user.get('real_name')}

    def send_message(self, message):
        """
            Requires this permission in Slack:
                Post messages as the app
                chat:write
        """
        result = self._client.api_call("chat.postMessage",
                                       channel=self._channel,
                                       text=message)
        if not result['ok']:
            self._logger.error("Couldn't send message to Slack because '{}', dropping: {}",
                               result['error'],
                               message)
