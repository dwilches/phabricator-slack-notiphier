
import logging
import os



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

    def __init__(self, phab_client, slack_client):
        self._phab_client = phab_client
        self._slack_client = slack_client

        phab_users = phab_client.get_users()
        slack_users = slack_client.get_users()
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
