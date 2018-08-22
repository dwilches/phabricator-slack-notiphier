
import logging
import os

from slackclient import SlackClient
from phabricator import Phabricator


class Users:
    """
    Bridge to Slack and Phabricators user APIs.
    The only rquisite is the full name must match between both systems.

    Usage:
        >>> users = Users(my_phab_url, my_phab_token, my_slack_token)
        >>> users['pparker']
        {'phid': 'PHID-USER-1234', 'phab_username': 'pparker', 'slack_id': 'U98765'}
        >>> users['PHID-USER-1234']
        {'phid': 'PHID-USER-1234', 'phab_username': 'pparker', 'slack_id': 'U98765'}
        >>> users.mention('pparker')
        '<@U98765>'
        >>> users.mention('PHID-USER-1234')
        '<@U98765>'
    """

    _logger = logging.getLogger('Users')
    _merged_users = {}

    def __init__(self, phabricator_url=None, phabricator_token=None, slack_token=None):
        self._phab_client = self._connect_phabricator(phabricator_url, phabricator_token)
        self._slack_client = self._connect_slack(slack_token)

        phab_users = self._get_phab_users()
        slack_users = self._get_slack_users()
        self._merged_users = self._merge_users(phab_users, slack_users)

    def __getitem__(self, userid):
        """
            Returns a user given its PHID or Phabricator username.

            :return
                An object in the form {phid, phab_username, slack_id} with the data of the user found.
                If a matching user is not found, None is returned.
        """
        if userid.startswith("PHID-USER-"):
            return self._merged_users.get(userid)

        return next((u for u in self._merged_users.values() if u['phab_username'] == userid), None)

    def mention(self, userid):
        """
            Returns a Slack mention given its PHID or Phabricator username.

            :return
                A mention in the form <@SLACKID>
        """

        user = self[userid]
        if not user:
            return None

        slack_id = user['slack_id']
        if not slack_id:
            return None

        return '<@{}>'.format(slack_id)

    def _connect_slack(self, slack_token):
        if not slack_token:
            slack_token = os.environ.get('NOTIPHIER_SLACK_TOKEN')
        if not slack_token:
            raise Exception("Can't find a token to connect to Slack.")

        try:
            return SlackClient(slack_token)
        except Exception as e:
            self._logger.error("Error connecting to Slack: " + str(e))
            raise

    def _connect_phabricator(self, phabricator_url, phabricator_token):
        if not phabricator_token:
            phabricator_token = os.environ.get('NOTIPHIER_PHABRICATOR_TOKEN')
        if not phabricator_token:
            raise Exception("Can't find a token to connect to Phabricator.")

        if not phabricator_url:
            phabricator_url = os.environ.get('NOTIPHIER_PHABRICATOR_URL')
        if not phabricator_url:
            raise Exception("Can't find Phabricator's URL.")

        try:
            return Phabricator(host=phabricator_url, token=phabricator_token)
        except Exception as e:
            self._logger.error("Error connecting to Phabricator: " + str(e))
            raise

    def _get_slack_users(self):
        """
            Requires this permission in Slack:
                View the workspace's list of members and their contact information
                users:read
        """
        self._logger.info("Getting list of users from Slack...")

        response = self._slack_client.api_call("users.list")
        if not response['ok']:
            raise Exception("Couldn't retrieve user list from Slack. Error: " + str(response['error']))

        return { user['real_name']: user['id'] for user in response['members']
                 if not user.get('is_bot', True) and user.get('real_name') }

    def _get_phab_users(self):
        self._logger.info("Getting list of users from Phabricator...")

        users = self._phab_client.user.search()
        return { user['phid']: (user['fields']['username'], user['fields']['realName'])
                 for user in users.data
                 if 'disabled' not in user['fields']['roles'] and
                    'bot' not in user['fields']['roles'] and
                    user['phid'].startswith('PHID-USER')}

    def _merge_users(self, phab_users, slack_users):
        """
            Grabs a user list from Slack and one from Phabricator and crosses them to return a dictionary with an entry
            per user, containing both Slack and Phab information for it.

            :return {phid: {phid, phab_username, slack_id}}
        """

        # Input looks like: 'Peter Parker'
        def get_slack_id(phab_fullname):
            if phab_fullname not in slack_users:
                self._logger.warn("Couldn't find this user in Slack: " + phab_fullname)
                return None

            return slack_users[phab_fullname]

        return {phid: {'phid': phid, 'phab_username': phab_names[0], 'slack_id': get_slack_id(phab_names[1])}
                for phid, phab_names in phab_users.items()}
