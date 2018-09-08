# Execute with:
#   Repos/slack-notiphier/src $ ../venv/bin/python -m  pytest ../tests

import json
import pytest
import os
from unittest.mock import patch

from slack_notiphier.webhook_firehose import WebhookFirehose


# TODO: these 3 fixtures should go in a common file


@pytest.fixture
def _fixture_env_vars():
    return {
        'NOTIPHIER_PHABRICATOR_URL': 'http://_phab_url_',
        'NOTIPHIER_PHABRICATOR_TOKEN': '_phab_token_',
        'NOTIPHIER_SLACK_TOKEN': '_slack_token_',
        'NOTIPHIER_SLACK_CHANNEL': '_slack_channel_',
    }


@pytest.fixture
def _fixture_phab_users():
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
def _fixture_slack_users():
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
def _execute_test_from_file(test_filename, Phabricator, Slack):
    with patch.dict(os.environ, _fixture_env_vars()), open("../tests/resources/" + test_filename, 'r') as fp_test_spec:
        test_spec = json.load(fp_test_spec)

        # Mock Phabricator calls
        instance_phab = Phabricator.return_value
        instance_phab.user.search.return_value = _fixture_phab_users()
        instance_phab.transaction.search.side_effect = _mock_phab_call("transaction.search",
                                                                       test_spec["mocked_phab_calls"])
        instance_phab.differential.revision.search.side_effect = _mock_phab_call("differential.revision.search",
                                                                                 test_spec["mocked_phab_calls"])

        # Mock Slack calls
        instance_slack = Slack.return_value
        instance_slack.api_call.side_effect = _mock_slack_api_call

        webhook = WebhookFirehose()

        # Process the message from the file as if it came from Phabricator's Firehose. It then asserts Slack was
        # invoked with the right message.
        try:
            webhook.handle(test_spec["request"])
            instance_slack.api_call.assert_called_with("chat.postMessage",
                                                       channel="_slack_channel_",
                                                       text=test_spec["expected_response"])
        except Exception as e:
            print("Exception in test. Some information about attempted calls:", instance_phab.mock_calls)
            raise e


def _mock_phab_call(method, mocked_phab_calls):

    def inner_phab_call_handler(*args, **kwargs):
        for expected_call in mocked_phab_calls[method]:
            if expected_call["kwargs"] == kwargs:
                return expected_call["response"]

        raise ValueError("Mock Phabricator called with unexpected arguments: method={} args={} kwargs={}"
                         .format(method, args, kwargs))

    return inner_phab_call_handler


def _mock_slack_api_call(method, *args, **kwargs):
    if method == "users.list":
        return _fixture_slack_users()

    if method == "chat.postMessage":
        return {'ok': True}

    raise ValueError("Invalid invocation to mocked slack_api_call: api_call({}, args={}, kwargs={})"
                     .format(method, args, kwargs))


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_welcome_message(Phabricator, Slack):
    """
        Simple test to ensure everything is correctly wired.
        Asserts we send the initial welcome message to Slack when the webhook starts running.
    """

    instance = Phabricator.return_value
    instance.user.search.return_value = _fixture_phab_users()
    instance = Slack.return_value
    instance.api_call.side_effect = _mock_slack_api_call

    with patch.dict(os.environ, _fixture_env_vars()):
        WebhookFirehose()
        instance.api_call.assert_called_with("chat.postMessage",
                                             channel="_slack_channel_",
                                             text="Slack Notiphier started running.")


def test_abandon_diff():
    _execute_test_from_file("abandon-diff.json")


def test_accept_diff():
    _execute_test_from_file("accept-diff.json")

