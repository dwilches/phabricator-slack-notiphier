
import pytest
import os

from unittest.mock import patch

from slack_notiphier import config, logger


@pytest.fixture(scope='session', autouse=True)
def setup_once():
    with patch.dict(os.environ, {'NOTIPHIER_CONFIG_FILE': '../tests/resources/slack-notiphier.cfg'}):
        config.reload()
        logger.reload()


# User     Valid in Phab              Valid in Slack
# aa             F (disabled)               T
# bb             T                          T
# cc             T                          T
# dd             T                          F (deleted)
# ee             T                          F (bot)
# ff             T                          T
# gg             T                          T
# hh             F (missing)                T
# ii             T                          F (missing)


@pytest.fixture
def users(_fixture_phab_users, _fixture_slack_users):
    return {
        'phab': _fixture_phab_users,
        'slack': _fixture_slack_users
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
            {
                "type": "USER",
                "phid": "PHID-USER-dd",
                "fields": {
                    "username": "ph-username-dd",
                    "realName": "User Name DD",
                    "roles": [],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-ee",
                "fields": {
                    "username": "ph-username-ee",
                    "realName": "User Name EE",
                    "roles": [],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-ff",
                "fields": {
                    "username": "ph-username-ff",
                    "realName": "User Name FF",
                    "roles": [],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-gg",
                "fields": {
                    "username": "ph-username-gg",
                    "realName": "User Name GG",
                    "roles": [],
                },
            },
            {
                "type": "USER",
                "phid": "PHID-USER-ii",
                "fields": {
                    "username": "ph-username-ii",
                    "realName": "User Name II",
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
                'id': "SLACK-ID-aa",
                'real_name': "User Name AA",
                'is_bot': False,
                'deleted': False,
            },
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
            },
            {
                'id': "SLACK-ID-ff",
                'real_name': "User Name FF",
                'is_bot': False,
                'deleted': False,
            },
            {
                'id': "SLACK-ID-gg",
                'real_name': "User Name GG",
                'is_bot': False,
                'deleted': False,
            },
            {
                'id': "SLACK-ID-hh",
                'real_name': "User Name HH",
                'is_bot': False,
                'deleted': False,
            },
        ]
    }
