# Execute with:
#   Repos/slack-notiphier/src $ ../venv/bin/python -m  pytest ../tests

import pytest
import os
from unittest.mock import patch, MagicMock

from slack_notiphier.slack_client import SlackClient
from slack_notiphier.phab_client import PhabClient
from slack_notiphier.users import Users
from slack_notiphier.config import reload_config

with patch.dict(os.environ, {'NOTIPHIER_CONFIG_FILE': '../tests/resources/slack-notiphier.cfg'}):
    reload_config()


@pytest.fixture
def fixture_phab_users():
    return {
        'data': [
            {
                "type": "USER",
                "phid": "PHID-USER-aa",
                "fields": {
                    "username": "ph-username-aa",
                    "realName": "PH Username AA",
                    "roles": ["disabled"],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-bb",
                "fields": {
                    "username": "ph-username-bb",
                    "realName": "User Name BB",
                    "roles": [],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-cc",
                "fields": {
                    "username": "ph-username-cc",
                    "realName": "User Name CC",
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
                'real_name': "User Name BB",
                'is_bot': False,
                'deleted': False,
            },
            {
                'id': "SLACK-ID-cc",
                'real_name': "User Name CC",
                'is_bot': False,
                'deleted': False,
            },
            {
                'id': "SLACK-ID-dd",
                'real_name': "User Name DD",
                'is_bot': False,
                'deleted': True,
            },
            {
                'id': "SLACK-ID-ee",
                'real_name': "User Name EE",
                'is_bot': True,
                'deleted': False,
            }
        ]
    }


@patch("phabricator.Phabricator")
def test_phab_get_users(Phabricator, fixture_phab_users):

    instance = Phabricator.return_value
    instance.user.search.return_value = fixture_phab_users

    phab_client = PhabClient()
    users = phab_client.get_users()

    assert Phabricator.call_count == 1
    Phabricator.assert_called_with(host='http://_phab_url_/api/', token='_phab_token_')

    assert users == {
        'PHID-USER-bb': ('ph-username-bb', 'User Name BB'),
        'PHID-USER-cc': ('ph-username-cc', 'User Name CC')
    }


@patch("phabricator.Phabricator")
def test_wrong_phab_url(Phabricator):

    instance = Phabricator.return_value
    instance.conduit.ping = MagicMock(side_effect=KeyError('Invalid URL or something'))
    instance.user.search.return_value = []

    with pytest.raises(Exception):
        PhabClient()


@patch("slackclient.SlackClient")
def test_slack_get_users(Slack, fixture_slack_users):

    instance = Slack.return_value
    instance.api_call.return_value = fixture_slack_users

    slack_client = SlackClient()
    users = slack_client.get_users()

    assert Slack.call_count == 1
    Slack.assert_called_with('_slack_token_')
    instance.api_call.assert_called_with("users.list")

    assert users == {
        "User Name BB": "SLACK-ID-bb",
        "User Name CC": "SLACK-ID-cc",
    }


@patch("slackclient.SlackClient")
def test_wrong_slack_token(Slack):

    instance = Slack.return_value
    instance.api_call.return_value = {
        'ok': False,
        'error': "invalid_auth",
    }

    slack_client = SlackClient()
    with pytest.raises(Exception):
        slack_client.get_users()


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_get_users(Phabricator, Slack, fixture_phab_users, fixture_slack_users):

    instance = Phabricator.return_value
    instance.user.search.return_value = fixture_phab_users
    instance = Slack.return_value
    instance.api_call.return_value = fixture_slack_users

    phab_client = PhabClient()
    slack_client = SlackClient()
    users = Users(phab_client, slack_client)
    instance.api_call.assert_called_with("users.list")

    expected_user_2 = {
        'phab_username': "ph-username-bb",
        'phid': "PHID-USER-bb",
        'slack_id': "SLACK-ID-bb",
    }
    expected_user_3 = {
        'phab_username': "ph-username-cc",
        'phid': "PHID-USER-cc",
        'slack_id': "SLACK-ID-cc",
    }

    assert expected_user_2 == users["PHID-USER-bb"]
    assert expected_user_2 == users["ph-username-bb"]
    assert expected_user_3 == users["PHID-USER-cc"]
    assert expected_user_3 == users["ph-username-cc"]

    assert users["PHID-USER-aa"] is None
    assert users["ph-username-aa"] is None
    assert users["non-existent"] is None


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_mention_users(Phabricator, Slack, fixture_phab_users, fixture_slack_users):

    instance = Phabricator.return_value
    instance.user.search.return_value = fixture_phab_users
    instance = Slack.return_value
    instance.api_call.return_value = fixture_slack_users

    phab_client = PhabClient()
    slack_client = SlackClient()
    users = Users(phab_client, slack_client)
    instance.api_call.assert_called_with("users.list")

    assert users.get_mention("PHID-USER-bb") == "<@SLACK-ID-bb>"
    assert users.get_mention("PHID-USER-cc") == "<@SLACK-ID-cc>"
    assert users.get_mention("ph-username-bb") == "<@SLACK-ID-bb>"
    assert users.get_mention("ph-username-cc") == "<@SLACK-ID-cc>"
