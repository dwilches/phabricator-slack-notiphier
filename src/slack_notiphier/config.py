
import json


with open("/etc/slack-notiphier.cfg") as config_fp:
    _config = json.load(config_fp)


def get_config(name, default):
    return _config.get(name, default)
