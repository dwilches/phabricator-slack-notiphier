# phabricator-slack-notifier
Posts messages in Slack about interesting activity in the Phabricator's feed, mentioning interested users

## Sample config file
    
    $ cat /etc/slack-notiphier.cfg 
    {
        "log_level": "INFO",
        "phabricator_url": "https://phabricator.example.com",
        "phabricator_token": "api-AAAAAAAAAAAAAa",
        "phabricator_webhook_hmac": "BBBBBBBBBBBBB",
        "slack_token": "xoxa-CCCCCCCCCCCCC",
        
        "channels": {
                "default": "#general",
                "SomeOtherRepo": "#important"
        }
    }
