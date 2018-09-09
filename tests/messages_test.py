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
        instance_phab.maniphest.search.side_effect = _mock_phab_call("maniphest.search",
                                                                     test_spec["mocked_phab_calls"])

        # Mock Slack calls
        instance_slack = Slack.return_value
        instance_slack.api_call.side_effect = _mock_slack_api_call

        webhook = WebhookFirehose()

        # Process the message from the file as if it came from Phabricator's Firehose. It then asserts Slack was
        # invoked with the right message.
        try:
            webhook.handle(test_spec["request"])

            for expected in test_spec["expected_responses"]:
                instance_slack.api_call.assert_any_call("chat.postMessage",
                                                        channel="_slack_channel_",
                                                        text=expected)
        except Exception as e:
            print("Exception in test. Some information about attempted calls:", instance_phab.mock_calls)
            raise e


def _mock_phab_call(method, mocked_phab_calls):

    def inner_phab_call_handler(*args, **kwargs):
        if method not in mocked_phab_calls:
            raise ValueError("Mock Phabricator called with unexpected method: method={} valid methods={}"
                             .format(method, mocked_phab_calls.keys()))

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

    phab_instance = Phabricator.return_value
    phab_instance.user.search.return_value = _fixture_phab_users()

    slack_instance = Slack.return_value
    slack_instance.api_call.side_effect = _mock_slack_api_call

    with patch.dict(os.environ, _fixture_env_vars()):
        WebhookFirehose()
        slack_instance.api_call.assert_called_with("chat.postMessage",
                                                   channel="_slack_channel_",
                                                   text="Slack Notiphier started running.")


# Task Tests

def test_task_create():
    _execute_test_from_file("task-create.json")


def test_task_add_comment():
    _execute_test_from_file("task-add-comment.json")


def test_task_add_comment_own():
    _execute_test_from_file("task-add-comment-own.json")


def test_task_claim():
    _execute_test_from_file("task-claim.json")


def test_task_assign():
    _execute_test_from_file("task-assign.json")


#def test_task_add_subscriber():
#    _execute_test_from_file("task-add-subscriber.json")


def test_task_change_priority():
    _execute_test_from_file("task-change-priority.json")


def test_task_change_priority_own():
    _execute_test_from_file("task-change-priority-own.json")


def test_task_change_status():
    _execute_test_from_file("task-change-status.json")


def test_task_change_status_own():
    _execute_test_from_file("task-change-status-own.json")


# Diff Revision Tests

def test_diff_create():
    _execute_test_from_file("diff-create.json")


def test_diff_update():
    _execute_test_from_file("diff-update.json")


def test_diff_abandon():
    _execute_test_from_file("diff-abandon.json")


def test_diff_reclaim():
    _execute_test_from_file("diff-reclaim.json")


def test_diff_accept():
    _execute_test_from_file("diff-accept.json")


def test_diff_request_changes():
    _execute_test_from_file("diff-request-changes.json")


def test_diff_commandeer():
    _execute_test_from_file("diff-commandeer.json")


def test_diff_add_comment():
    _execute_test_from_file("diff-add-comment.json")


def test_diff_add_comment_own():
    _execute_test_from_file("diff-add-comment-own.json")
