# Slack Notiphier
Posts messages in [Slack](https://slack.com/) about interesting activity in the [Phabricator's](https://www.phacility.com/) feed, mentioning users about interesting activity.


## Installation

#### Install `Slack Notiphier` in your server

To install, just clone this repository in your server and execute Slack Notiphier like this:

    $ python3 -m slack_notiphier

By default, Slack Notiphier searches for its config file in `/etc/slack-notiphier.cfg`,  but you can override the
default path with the environment variable `NOTIPHIER_CONFIG_FILE`.
 
The config file should have contents similar to this: `cfg/slack-notiphier.cfg`


#### Configure the `Herald Firehose Webhook` to forward events to `Slack Notiphier`

Now, all you need to do is to create a new [`Herald`](https://secure.phabricator.com/book/phabricator/article/herald/)
Firehose Webhook and make it point to the server where `Slack Notiphier` is running. To configure this webhook:
- In Phabricator, go to `Herald`
- Click `Create Webhook`
   - In `Name` write `Slack Notiphier` or any name you feel like.
   - In `URI` write `http://<my-server's IP>:5000/firehose`, this is the url where `Slack Notiphier` is listening.
     For example if your server's IP is `33.55.44.66` then this field must be: `http://33.55.44.66:5000/firehose`
   - In `Status` select `Firehose`.

That's it. If you restart `Slack Notiphier` you should see in Slack a message similar to `Slack Notiphier started running.`


### Config file elements

- **`log_level`**: Optional, default `"INFO"`. Sets how verbose you want the output of Slack Notiphier to be. This output goes
  to the standard output.
- **`phabricator_url`**: No default, mandatory. Set this to the full url of your server with the `http/https` prefix, 
  like `"https://phabricator.example.com"`. Notice you shouldn't include the `/api` path at the end that is needed to make 
  `Conduit` calls.
- **`phabricator_token`** No default, mandatory. Paste here a [`Conduit API Token`](https://secure.phabricator.com/book/phabricator/article/conduit/). 
  You can generate these from inside 
  Phabricator:
   - Click on your username.
   - Select `Settings`.
   - Select `Conduit API Tokens`.
   - Select `Generate Token`.
   - A token similar to this one will be generated: `api-abcdefghijklmopqrstuvwxyz123`.
   - Paste that token in the `phabricator_token` field of `/etc/slack-notiphier.cfg`.
- **`phabricator_webhook_hmac`**: No default, mandatory. This HMAC is used to ensure the messages `Slack Notiphier` is processing
  are coming from your Phabricator server (and not from an attacker). You can get this value from Phabricator. 
  Go to Herald and click your *Herald Firehose Webhook*, then click on `View HMAC Key` to see the HMAC value.
- **`slack_token`**: This is the `xoxa` or `xoxp` token of a Slack app. To get this, go to your
  [Slack API](https://api.slack.com/apps) website and click on `Create New App`.
   - In `App Name` write `Slack Notiphier`.
   - In `Development Slack Workspace` select your organization.
   - Click `Create App`.
   - Now, inside your new app, click `OAuth & Permissions`.
   - Under `Scopes` select `chat:write` and `users:read`.
   - Click `Save Changes` and the request one of your admins to approve the app for installation.
   - Once the app is approved, refresh the page and install the app in your workspace.
   - Now, under `OAuth & Permissions` you should have a new token in the section `Access Token`.
   - Click on `Show` and copy this token to `Slack Notihier's config file.
- **`channels`**: No default, mandatory. You can use this field to direct messages affecting certain repositories to
  only certain channels. You need at least a setting here `default` and then add as many extra rules as you want, for example:
```yaml
    channels:
        default: "#general"
        MyImportantRepo: "#important"
        NotSoImportantRepo: "#notimportant"
```
 - **`host`**: Optional, default `"0.0.0.0"`. Specifies in which network interface `Slack Notiphier` should listen. 
   By default it will listen on every interface (`0.0.0.0`) but you can specify here only one IP in case you want to 
   restrict access.
 - **`port`**: Optional, default `5000`. Specifies in which port `Slack Notiphier` should listen. 

### Executing locally

You can execute `slack_notiphier` like this:

```bash
$ cd slack-notiphier/src
$ ../venv/bin/python -m slack_notiphier
```

Also ensure you are using `0.0.0.0` as your `host` in the config file, or that you are using default value.


**NOTE:** 
> Slack Notiphier validates the signature of the incoming messages to ensure they come from the right Phabricator server. So take into account you'll need to pass the `X-Phabricator-Webhook-Signature` HTTP header if you plan on passing messages with `curl`.

### Testing

Tests are done through [`pytest`](https://docs.pytest.org/en/latest/), before making a change to the Notiphier 
ensure all the tests are still passing, and add new tests if needed.

Execute tets with:

```bash
$ cd slack-notiphier/src
$ ../venv/bin/python -m  pytest ../tests/
```

