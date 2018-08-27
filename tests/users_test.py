# Execute with:
#   Repos/slack-notiphier/src $ ../venv/bin/python -m  pytest ../tests

import pytest
import os
from unittest.mock import patch, MagicMock

from slack_notiphier.slack_client import SlackClient
from slack_notiphier.phab_client import PhabClient
from slack_notiphier.users import Users


@pytest.fixture
def fixture_env_vars():
    return {
        'NOTIPHIER_PHABRICATOR_URL': 'http://_phab_url_',
        'NOTIPHIER_PHABRICATOR_TOKEN': '_phab_token_',
        'NOTIPHIER_SLACK_TOKEN': '_slack_token_',
        'NOTIPHIER_SLACK_CHANNEL': '_slack_channel_',
    }


@pytest.fixture
def fixture_phab_users():
    return {
        'data': [
            {
                "type": "USER",
                "phid": "PHID-USER-aa",
                "fields": {
                    "username": "username-1",
                    "realName": "User Name 1",
                    "roles": ["disabled"],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-bb",
                "fields": {
                    "username": "username-2",
                    "realName": "User Name 2",
                    "roles": [],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-cc",
                "fields": {
                    "username": "username-3",
                    "realName": "User Name 3",
                    "roles": [],
                },
            },
        ]
    }


@pytest.fixture
def fixture_slack_users():
    return {
        'ok': True,
        'members': [
            {
                'id': "SLACK-ID-bb",
                'real_name': "User Name 2",
                'is_bot': False,
                'deleted': False,
            },
            {
                'id': "SLACK-ID-cc",
                'real_name': "User Name 3",
                'is_bot': False,
                'deleted': False,
            },
            {
                'id': "SLACK-ID-dd",
                'real_name': "User Name 4",
                'is_bot': False,
                'deleted': True,
            },
            {
                'id': "SLACK-ID-ee",
                'real_name': "User Name 5",
                'is_bot': True,
                'deleted': False,
            }
        ]
    }


@patch("phabricator.Phabricator")
def test_phab_get_users(Phabricator, fixture_env_vars, fixture_phab_users):

    instance = Phabricator.return_value
    instance.user.search.return_value = fixture_phab_users

    with patch.dict(os.environ, fixture_env_vars):
        phab_client = PhabClient()
        users = phab_client.get_users()

        assert Phabricator.call_count == 1
        Phabricator.assert_called_with(host='http://_phab_url_/api/', token='_phab_token_')

        assert users == {
            'PHID-USER-bb': ('username-2', 'User Name 2'),
            'PHID-USER-cc': ('username-3', 'User Name 3')
        }


@patch("phabricator.Phabricator")
def test_wrong_phab_url(Phabricator, fixture_env_vars):

    instance = Phabricator.return_value
    instance.conduit.ping = MagicMock(side_effect=KeyError('Invalid URL or something'))
    instance.user.search.return_value = []

    with patch.dict(os.environ, fixture_env_vars):
        with pytest.raises(Exception):
            PhabClient()


@patch("slackclient.SlackClient")
def test_slack_get_users(Slack, fixture_env_vars, fixture_slack_users):

    instance = Slack.return_value
    instance.api_call.return_value = fixture_slack_users

    with patch.dict(os.environ, fixture_env_vars):
        slack_client = SlackClient()
        users = slack_client.get_users()

        assert Slack.call_count == 1
        Slack.assert_called_with('_slack_token_')
        instance.api_call.assert_called_with("users.list")

        assert users == {
            "User Name 2": "SLACK-ID-bb",
            "User Name 3": "SLACK-ID-cc",
        }


@patch("slackclient.SlackClient")
def test_wrong_slack_token(Slack, fixture_env_vars):

    instance = Slack.return_value
    instance.api_call.return_value = {
        'ok': False,
        'error': "invalid_auth",
    }

    with patch.dict(os.environ, fixture_env_vars):
        slack_client = SlackClient()
        with pytest.raises(Exception):
            slack_client.get_users()


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_get_users(Phabricator, Slack, fixture_env_vars, fixture_phab_users, fixture_slack_users):

    instance = Phabricator.return_value
    instance.user.search.return_value = fixture_phab_users
    instance = Slack.return_value
    instance.api_call.return_value = fixture_slack_users

    with patch.dict(os.environ, fixture_env_vars):
        phab_client = PhabClient()
        slack_client = SlackClient()
        users = Users(phab_client, slack_client)
        instance.api_call.assert_called_with("users.list")

        expected_user_2 = {
            'phab_username': "username-2",
            'phid': "PHID-USER-bb",
            'slack_id': "SLACK-ID-bb",
        }
        expected_user_3 = {
            'phab_username': "username-3",
            'phid': "PHID-USER-cc",
            'slack_id': "SLACK-ID-cc",
        }

        assert expected_user_2 == users["PHID-USER-bb"]
        assert expected_user_2 == users["username-2"]
        assert expected_user_3 == users["PHID-USER-cc"]
        assert expected_user_3 == users["username-3"]

        assert users["PHID-USER-aa"] is None
        assert users["username-1"] is None
        assert users["non-existent"] is None


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_mention_users(Phabricator, Slack, fixture_env_vars, fixture_phab_users, fixture_slack_users):

    instance = Phabricator.return_value
    instance.user.search.return_value = fixture_phab_users
    instance = Slack.return_value
    instance.api_call.return_value = fixture_slack_users

    with patch.dict(os.environ, fixture_env_vars):
        phab_client = PhabClient()
        slack_client = SlackClient()
        users = Users(phab_client, slack_client)
        instance.api_call.assert_called_with("users.list")

        assert users.get_mention("PHID-USER-bb") == "<@SLACK-ID-bb>"
        assert users.get_mention("PHID-USER-cc") == "<@SLACK-ID-cc>"
        assert users.get_mention("username-2") == "<@SLACK-ID-bb>"
        assert users.get_mention("username-3") == "<@SLACK-ID-cc>"
