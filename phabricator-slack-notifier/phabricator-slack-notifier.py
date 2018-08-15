#!/usr/bin/env python
#
# Phabricator Slack notifier
# Sends the Phabricator event stream to Slack
#
# Enable hook:
#   /opt/phabricator/phabricator/bin/config set feed.http-hooks '["http://localhost:8080/handler"]'
#
# Can be tested with:
#   curl -XPOST  'http://localhost:8080/handler' --data-urlencode 'storyText=peter added a comment in D1234.'

from bottle import run, route, post, request, HTTPResponse
from phabricator import Phabricator
import re
import string
from textwrap import dedent
import os
import requests
import sys
import traceback
import yaml

from users import init_users, get_user, make_mention


# get repo name from a diff ID
def get_repo_name(diff_id):
    diff_id = diff_id.replace('D', '')
    repo_id = get_diff(diff_id)['repositoryPHID']
    if repo_id is None:
        return None
    repo_name = query_by_phid(repo_id)['name']
    return repo_name


def get_author_phid(diff_id):
    phab_object = get_diff(diff_id) if diff_id.startswith('D') else get_commit(diff_id)
    return phab_object['authorPHID']


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


# post message to slack
def post_message(message, channel):
    data = {
        'channel': channel,
        'text': message,
        'icon_emoji': ':phabricator:',
        'link_names': 1
    }

    print(message)
    if config['webhook_url']:
        requests.post(config['webhook_url'], json=data)


def _get_reviewer_mentions(diff):
    reviewers_phids = get_diff(diff)['reviewers'].keys()
    if reviewers_phids:
        mentions = []
        for phid in reviewers_phids:
            mention = make_mention(phid)
            if mention:
                mentions.append(mention)
        return ' '.join(mentions)

    return None


def parse_feed(config, story_text):
    diff = re.search('\sD\d+', story_text)
    if diff:
        diff = diff.group(0).strip()
    task = re.search('\sT\d+', story_text)
    if task:
        task = task.group(0).strip().strip()
    commit = re.search('\s(r[A-Z]+\w+):', story_text)
    if commit:
        commit = commit.group(1)
    build = re.search('\sB\d+', story_text)
    if build:
        build = build.group(0).strip()
    wiki = re.search('edited the content of (.*).', story_text)
    if wiki:
        wiki = wiki.group(1).replace(' ', '_')

    if diff:
        message = string.replace(story_text, diff, '<' + config['phab_url'] + '/' + diff + '|' + diff + '>')
    elif task:
        message = string.replace(story_text, task, '<' + config['phab_url'] + '/' + task + '|' + task + '>')
    elif commit:
        message = string.replace(story_text, commit, '<' + config['phab_url'] + '/' + commit + '|' + commit + '>')
    elif build:
        message = string.replace(story_text, build, '<' + config['phab_url'] + '/' + build + '|' + build + '>')
    elif wiki:
        message = string.replace(story_text, wiki, '<' + config['phab_url'] + '/w/' + wiki + '|' + wiki + '>')
    else:
        message = story_text

    # Add mentions to Slack
    reviewers = re.search('(\S+) added (?:a reviewer|reviewers) for D\d+: .*: (.*)$', story_text)
    if reviewers:
        who_did_it = reviewers.group(1)
        for new_reviewer in reviewers.group(2).split(", "):
            if who_did_it != new_reviewer:
                reviewer_mention = make_mention(new_reviewer)
                message = string.replace(message, new_reviewer, reviewer_mention)

    commentor = re.search('(\S+) added (a comment|inline comments) to [Dr]', story_text)
    if commentor:
        author_phid = get_author_phid(diff or commit)
        commentor_user = get_user(commentor.group(1))
        # Don't notify yourself about your own comments
        if commentor_user and commentor_user['phid'] != author_phid:
            author_mention = make_mention(author_phid)
            message = author_mention + ' ' + message

    diff_accepted = re.search('\S+ accepted D\d+:', story_text)
    if diff_accepted:
        author_phid = get_author_phid(diff)
        message = make_mention(author_phid) + ' ' + message + ' ' + ':accepted:'

    diff_requested_changes = re.search('\S+ requested changes to D\d+:', story_text)
    if diff_requested_changes:
        author_phid = get_author_phid(diff)
        message = make_mention(author_phid) + ' ' + message + ' ' + ':triangular_flag_on_post:'

    concern_raised = re.search('\S+ raised a concern with', story_text)
    if concern_raised:
        author_phid = get_author_phid(commit)
        message = make_mention(author_phid) + ' ' + message + ' ' + ':triangular_flag_on_post:'

    # Diffs created with reviewers will notify the reviewers
    diff_created = re.search('\S+ created D\d+:', story_text)
    if diff_created:
        reviewer_mentions = _get_reviewer_mentions(diff)
        if reviewer_mentions:
            message = message + ' (reviewers: ' + reviewer_mentions + ')'

    review_requested = re.search('\S+ requested review of D\d+:', story_text)
    if review_requested:
        reviewer_mentions = _get_reviewer_mentions(diff)
        if reviewer_mentions:
            message = reviewer_mentions + ' ' + message

    return message, diff, commit


@post('/handler')
def handler():
    story_text = request.params['storyText']

    try:
        (message, diff, commit) = parse_feed(config, story_text)

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
            ''').format(os.path.basename(__file__), str(e), story_text, traceback.format_exc())

        post_message(message, channel='#dev-notify')


@route('/health')
def health():
    return "OK\n"


def load_config(config_file):
    with open(config_file, 'r') as ymlconf:
        config = yaml.load(ymlconf)

    return {
        'phab_url': config['phabricator_url'],
        'api_url': config['phabricator_url'] + '/api/',
        'webhook_url': config['slack']['webhook_url'],    # For sending messages
        'phabricator_token': config['phabricator_token'],
        'slack_token': config['slack']['token']           # For getting the list of users
    }


if __name__ == '__main__':
    default_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../etc/config.yaml')
    config = load_config(sys.argv[1] if len(sys.argv) >= 2 else default_filename)

    phab = Phabricator(host=config['api_url'], token=config['phabricator_token'])

    init_users(phab_client=phab, slack_token=config['slack_token'])

    post_message("*Phabricator Slack notifier* started running", channel='#dev-notify')

    run(host='localhost', port=8080)
