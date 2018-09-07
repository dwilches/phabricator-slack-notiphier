# Execute with:
#   Repos/slack-notiphier/src $ ../venv/bin/python -m  pytest ../tests

import pytest
import os
from unittest.mock import patch

from slack_notiphier.webhook_firehose import WebhookFirehose


# TODO: these 3 fixtures should go in a common file


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


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_welcome_message(Phabricator, Slack, fixture_env_vars, fixture_phab_users, fixture_slack_users):
    """
        Simple test to ensure everything is correctly wired.
        Asserts we send the initial welcome message to Slack when the webhook starts running.
    """

    instance = Phabricator.return_value
    instance.user.search.return_value = fixture_phab_users
    instance = Slack.return_value
    instance.api_call.side_effect = slack_api_call

    with patch.dict(os.environ, fixture_env_vars):
        WebhookFirehose()
        instance.api_call.assert_called_with("chat.postMessage",
                                             channel="_slack_channel_",
                                             text="Slack Notiphier started running.")


def slack_api_call(method, *args, **kwargs):
    if method == "users.list":
        return fixture_slack_users()

    if method == "chat.postMessage":
        return {'ok': True}

    raise ValueError("Invalid invocation to mocked slack_api_call: api_call({}, args={}, kwargs={})"
                     .format(method, args, kwargs))
