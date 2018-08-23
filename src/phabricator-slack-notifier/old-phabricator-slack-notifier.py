#!/usr/bin/env python
#
# Phabricator Slack notifier
# Sends the Phabricator event stream to Slack
#
# Enable hook:
#   /opt/phabricator/phabricator/bin/config set feed.http-hooks '["http://localhost:8080/handler"]'
#

from bottle import run, route, post, request, HTTPResponse
import re
import string
from textwrap import dedent
import os
import yaml
from phabricator import Phabricator
from slackclient import SlackClient
import traceback

config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../etc/config.yaml')
with open(config_file, 'r') as ymlconf:
    config = yaml.load(ymlconf)

# phabricator URL
url = config['phabricator_url']
api_url = url + '/api/'

# phabricator token
phabricator_token = config['phabricator_token']

# slack token (Only to get list of users. Sending a message is done through a webhook)
slack_token = config['slack_token']

phab = Phabricator(host=api_url, token=phabricator_token)
slack_client = SlackClient(slack_token)

re_phab_full_name = re.compile(r'.*\((.+)\)')


def get_slack_users():
    print("Getting list of users from Slack")
    response = slack_client.api_call("users.list")
    if not response['ok']:
        raise Exception("Couldn't retrieve user list from Slack. Error: {}".format(response['error']))

    return { user['real_name']: user['id'] for user in response['members']
                                           if not user.get('is_bot', True) and user.get('real_name') }


# Input looks like: 'pparker (Peter Parker)'
def make_slack_mention(phab_fullname):
    match = re_phab_full_name.match(phab_fullname)
    if not match:
        raise Exception("Couldn't find how to mention: " + phab_fullname)

    slack_user_id = slack_users.get(match.group(1))
    if not slack_user_id:
        raise Exception("Couldn't find how to mention: " + phab_fullname)

    return '<@{}>'.format(slack_user_id)


# get repo name from a diff ID
def get_repo_name(diff_id):
    diff_id = diff_id.replace('D', '')
    repo_id = get_diff(diff_id)['repositoryPHID']
    if repo_id is None:
        return None
    repo_name = query_by_phid(repo_id)['name']
    return repo_name


# get author name from a diff or commit ID (D1234 or rCONSOLE123456)
def get_author_name(object_id):
    if object_id.startswith('D'):
        author_id = get_diff(object_id)['authorPHID']
    else:
        author_id = get_commit(object_id)['authorPHID']

    return query_by_phid(author_id)['name']


def query_by_phid(phid):
    result = phab.phid.query(phids=[phid])
    return result[phid] if result else None


def get_diff(diff_id):
    diff_id = diff_id.replace('D', '')
    return phab.differential.query(ids=[diff_id])[0]


def get_commit(commit_id):
    result = phab.diffusion.querycommits(names=[commit_id])
    commit_phid = result.identifierMap[commit_id]
    return result['data'][commit_phid]


# For those whose usernames don't match
def get_slack_user_name(phab_user_name):
    overrides = {
    }

    if phab_user_name in overrides:
        return overrides[phab_user_name]
    else:
        return phab_user_name


# post message to slack
def post_message(message, channel):
    slack_client.api_call("chat.postMessage", channel=channel, text=message, link_names=True)


@post('/handler')
def handler():
    story_text = request.params['storyText']

    try:
        diff = re.search('\sD\d+', story_text)
        if diff:
            diff = diff.group(0).strip()
        task = re.search('\sT\d+', story_text)
        if task:
            task = task.group(0).strip().strip()
        commit = re.search('\sr[A-Z]+\S+:', story_text)
        if commit:
            commit = commit.group(0).replace(':', '').strip()
        build = re.search('\sB\d+', story_text)
        if build:
            build = build.group(0).strip()
        wiki = re.search('edited the content of (.*).', story_text)
        if wiki:
            wiki = wiki.group(1).replace(' ', '_')

        if diff:
            message = string.replace(story_text, diff, '<' + url + '/' + diff + '|' + diff + '>')
        elif task:
            message = string.replace(story_text, task, '<' + url + '/' + task + '|' + task + '>')
        elif commit:
            message = string.replace(story_text, commit, '<' + url + '/' + commit + '|' + commit + '>')
        elif build:
            message = string.replace(story_text, build, '<' + url + '/' + build + '|' + build + '>')
        elif wiki:
            message = string.replace(story_text, wiki, '<' + url + '/w/' + wiki + '|' + wiki + '>')
        else:
            message = story_text

        # Add mentions to Slack
        reviewers = re.search('(\S+) added (?:a reviewer|reviewers) for D\d+: .*: (.*)$', story_text)
        if reviewers:
            who_did_it = reviewers.group(1)
            for reviewer in reviewers.group(2).split(", "):
                if who_did_it != reviewer:
                    message = string.replace(message, reviewer, '@' + get_slack_user_name(reviewer))
            message = message.rstrip('.')

        commentor = re.search('(\S+) added (a comment|inline comments) to (D|r)', story_text)
        if commentor:
            author_name = get_author_name(diff or commit)
            # Don't notify yourself about your own comments
            if commentor.group(1) not in [ author_name, 'jenkins', 'changebot' ]:
                message = '@' + get_slack_user_name(author_name) + ' ' + message

        diff_accepted = re.search('\S+ accepted D\d+:', story_text)
        if diff_accepted:
            author_name = get_author_name(diff)
            message = '@' + get_slack_user_name(author_name) + ' ' + message + ' ' + ':accepted:'

        diff_requested_changes = re.search('\S+ requested changes to D\d+:', story_text)
        if diff_requested_changes:
            author_name = get_author_name(diff)
            message = '@' + get_slack_user_name(author_name) + ' ' + message + ' ' + ':triangular_flag_on_post:'

        concern_raised = re.search('\S+ raised a concern with', story_text)
        if concern_raised:
            author_name = get_author_name(commit)
            message = '@' + get_slack_user_name(author_name) + ' ' + message + ' ' + ':triangular_flag_on_post:'

        # Diffs created with reviewers will notify the reviewers
        diff_created = re.search('\S+ created D\d+:', story_text)
        if diff_created:
            reviewers = get_diff(diff)['reviewers']
            if reviewers:
                reviewers = reviewers.keys()

            reviewers = [query_by_phid(reviewer) for reviewer in reviewers]
            reviewer_names = [reviewer['name'] for reviewer in reviewers if reviewer is not None]
            reviewer_names = [n for n in reviewer_names if n not in ('Engineering', 'Alpha', 'Omega')]

            if reviewer_names:
                slack_names = ['@' + get_slack_user_name(name) for name in reviewer_names]
                message = message + ' (reviewers: ' + (' '.join(slack_names)) + ')'

        review_requested = re.search('\S+ requested review of D\d+:', story_text)
        if review_requested:
            reviewers_phids = get_diff(diff)['reviewers'].keys()
            if reviewers_phids:
                reviewers = [query_by_phid(phid) for phid in reviewers_phids]
                reviewer_names = [reviewer['fullName'] for reviewer in reviewers
                                  if not reviewer or reviewer['typeName'] == "User"]

                slack_mentions = [make_slack_mention(name) for name in reviewer_names]
                message = ' '.join(slack_mentions) + ' ' + message

        print message

        post_message(message, channel='#dev-notify')

        # notify additional channels for certain repos
        if diff:
            repo = get_repo_name(diff)
            if repo is None:
                return HTTPResponse(status=200, body='No repo found')
            if repo in ['rSQUADRON', 'rCHEF']:
                post_message(message, channel='#release')
            if repo == 'rTERRAFORM':
                post_message(message, channel='#terraform')

        # notify additional channels for certain repos
        if commit:
            if 'rCHEF' in message or 'rSQUADRON' in message:
                post_message(message, channel='#release')
            if 'rTERRAFORM' in message:
                post_message(message, channel='#terraform')

    except Exception as e:
        message = dedent('''
            *Dang, {} hit a snag:* {}
            *Original message:* {}
            *Stacktrace:* {}
            ''').format(os.path.basename(__file__), str(e), message, traceback.format_exc())

        print message

        post_message(message, channel='#dev-notify')

@route('/health')
def health():
    return "OK\n"


slack_users = get_slack_users()

post_message("*Phabricator Slack notifier* started running", channel='#dev-notify')

run(host='localhost', port=8080)
