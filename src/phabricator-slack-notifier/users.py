
from slackclient import SlackClient

_users = {}


def _get_slack_users(slack_client):
    print("Getting list of users from Slack")
    response = slack_client.api_call("users.list")
    if not response['ok']:
        raise Exception("Couldn't retrieve user list from Slack. Error: {}".format(response['error']))

    return { user['real_name']: user['id'] for user in response['members']
             if not user.get('is_bot', True) and user.get('real_name') }


def _get_phab_users(phab_client):
    print("Getting list of users from Phabricator")
    users = phab_client.user.search()
    return { user['phid']: (user['fields']['username'], user['fields']['realName'])
             for user in users.data
             if 'disabled' not in user['fields']['roles'] and 'bot' not in user['fields']['roles'] }


def _get_users(phab_client, slack_client):
    """
        Grabs a user list from Slack and one from Phabricator and crosses them to return a dictionary with an entry
        per user, containing both Slack and Phab information for it.

        :return {phid: {phid, phab_username, slack_id}}
    """
    slack_users = _get_slack_users(slack_client)
    phab_users = _get_phab_users(phab_client)

    # Input looks like: 'Peter Parker'
    def get_slack_id(phab_fullname):
        if phab_fullname not in slack_users:
            print("Couldn't find this user in Slack: " + phab_fullname)
            return None

        return slack_users[phab_fullname]

    return {phid: {'phid': phid, 'phab_username': phab_names[0], 'slack_id': get_slack_id(phab_names[1])}
            for phid, phab_names in phab_users.items()}


def _get_user_by_phab_username(phab_username):
    for user in _users.values():
        if user['phab_username'] == phab_username:
            return user


def init_users(phab_client, slack_token):
    global _users
    slack_client = SlackClient(slack_token)
    _users = _get_users(phab_client, slack_client)


def get_user(userid):
    """ Receives either a PHID or a Phabricator username """
    if userid.startswith("PHID-USER-"):
        user = _users.get(userid, {'phid': None, 'phab_username': None, 'slack_id': None})
    else:
        user = _get_user_by_phab_username(userid)

    return user or {'phid': None, 'phab_username': None, 'slack_id': None}


def make_mention(userid):
    """ Receives either a PHID or a Phabricator username """

    # Don't add mentions for projects
    if userid and userid.startswith('PHID-PROJ'):
        return ''

    slack_id = get_user(userid)['slack_id']

    # If we don't know the slack_id show the username as is so the info is not lost
    if slack_id is None:
        return userid

    return '<@{}>'.format(slack_id)
