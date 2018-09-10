# Execute with:
#   Repos/slack-notiphier/src $ ../venv/bin/python -m  pytest ../tests

import json
import os
from unittest.mock import patch

import pytest

from slack_notiphier.webhook_firehose import WebhookFirehose
from slack_notiphier import config, logger

with patch.dict(os.environ, {'NOTIPHIER_CONFIG_FILE': '../tests/resources/slack-notiphier.cfg'}):
    config.reload()
    logger.reload()


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def _execute_test_from_file(test_filename, Phabricator, Slack, users):
    with open("../tests/resources/" + test_filename, 'r') as fp_test_spec:
        test_spec = json.load(fp_test_spec)

        # Mock Phabricator calls
        instance_phab = Phabricator.return_value
        instance_phab.user.search.return_value = users['phab']
        instance_phab.transaction.search.side_effect = _mock_phab_call("transaction.search",
                                                                       test_spec["mocked_phab_calls"])
        instance_phab.differential.revision.search.side_effect = _mock_phab_call("differential.revision.search",
                                                                                 test_spec["mocked_phab_calls"])
        instance_phab.maniphest.search.side_effect = _mock_phab_call("maniphest.search",
                                                                     test_spec["mocked_phab_calls"])
        instance_phab.project.search.side_effect = _mock_phab_call("project.search",
                                                                   test_spec["mocked_phab_calls"])
        instance_phab.diffusion.repository.search.side_effect = _mock_phab_call("diffusion.repository.search",
                                                                                test_spec["mocked_phab_calls"])
        instance_phab.diffusion.querycommits.side_effect = _mock_phab_call("diffusion.querycommits",
                                                                           test_spec["mocked_phab_calls"])

        # Mock Slack calls
        instance_slack = Slack.return_value
        instance_slack.api_call.side_effect = _mock_slack_api_call(users['slack'])

        webhook = WebhookFirehose()

        # Process the message from the file as if it came from Phabricator's Firehose. It then asserts Slack was
        # invoked with the right message.
        try:
            webhook.handle(test_spec["request"])

            for expected in test_spec["expected_responses"]:
                instance_slack.api_call.assert_any_call("chat.postMessage",
                                                        channel=expected['channel'],
                                                        attachments=expected['attachments'])
        except Exception as e:
            print("Exception in test. Some information about attempted Phab calls:", instance_phab.mock_calls)
            print("Exception in test. Some information about attempted Slack calls:", instance_slack.mock_calls)
            raise e


def _mock_phab_call(method, mocked_phab_calls):

    def inner_phab_call_handler(*args, **kwargs):
        if method not in mocked_phab_calls:
            raise ValueError("Mock Phabricator called with unexpected method: {} valid methods={}"
                             .format(method, mocked_phab_calls.keys()))

        for expected_call in mocked_phab_calls[method]:
            if expected_call["kwargs"] == kwargs:
                return expected_call["response"]

        raise ValueError("Mock Phabricator called with unexpected arguments: method={} args={} kwargs={}"
                         .format(method, args, kwargs))

    return inner_phab_call_handler


def _mock_slack_api_call(fixture_slack_users):

    def inner_slack_call_handler(method, *args, **kwargs):
        if method == "users.list":
            return fixture_slack_users

        if method == "chat.postMessage":
            return {'ok': True}

        raise ValueError("Invalid invocation to mocked slack_api_call: api_call({}, args={}, kwargs={})"
                         .format(method, args, kwargs))

    return inner_slack_call_handler


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_welcome_message(Phabricator, Slack, users):
    """
        Simple test to ensure everything is correctly wired.
        Asserts we send the initial welcome message to Slack when the webhook starts running.
    """

    phab_instance = Phabricator.return_value
    phab_instance.user.search.return_value = users['phab']

    slack_instance = Slack.return_value
    slack_instance.api_call.side_effect = _mock_slack_api_call(users['slack'])

    WebhookFirehose()
    slack_instance.api_call.assert_called_with("chat.postMessage",
                                               channel="_slack_channel_",
                                               attachments=[{
                                                   'text': "Slack Notiphier started running.",
                                                   'color': '#28D7E5',
                                               }])


# Task Tests


@pytest.fixture(params=[
    "task-create.json",
    "task-add-comment.json",
    "task-add-comment-with-mention.json",
    "task-add-comment-own.json",
    "task-claim.json",
    "task-assign.json",
    "task-change-priority.json",
    "task-change-priority-own.json",
    "task-change-status.json",
    "task-change-status-own.json",
])
def task_test_file(request):
    return request.param


def test_tasks(task_test_file, users):
    _execute_test_from_file(task_test_file, users=users)


# Diff Revision Tests


@pytest.fixture(params=[
    "diff-create.json",
    "diff-update.json",
    "diff-abandon.json",
    "diff-reclaim.json",
    "diff-accept.json",
    "diff-request-changes.json",
    "diff-commandeer.json",
    "diff-add-comment.json",
    "diff-add-comment-own.json",
    "diff-add-comment-with-mention.json",
    "diff-create-notify-other-channel.json",
    "diff-add-comment-inline.json",
    "diff-add-comment-inline-own.json",
])
def diff_test_file(request):
    return request.param


def test_diffs(diff_test_file, users):
    _execute_test_from_file(diff_test_file, users=users)


# Commit Tests


@pytest.fixture(params=[
    "commit-add-comment.json",
])
def commit_test_file(request):
    return request.param


def test_commits(commit_test_file, users):
    _execute_test_from_file(commit_test_file, users=users)


# Project Tests


@pytest.fixture(params=[
    "proj-create.json",
])
def proj_test_file(request):
    return request.param


def test_projs(proj_test_file, users):
    _execute_test_from_file(proj_test_file, users=users)


# Repository Tests


@pytest.fixture(params=[
    "repo-create.json",
])
def repo_test_file(request):
    return request.param


def test_repos(repo_test_file, users):
    _execute_test_from_file(repo_test_file, users=users)
