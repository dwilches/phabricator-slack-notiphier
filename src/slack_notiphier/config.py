
import json
import os

_no_default = object()
_config = {}


def get_config(name, default=_no_default):
    if default is _no_default:
        value = _config.get(name)
        if not value:
            raise ValueError("No value found for '{}' in config file: {}".format(name, _config_file))
        return value
    else:
        return _config.get(name, default)


def reload_config():
    global _config
    _config_file = os.getenv('NOTIPHIER_CONFIG_FILE', "/etc/slack-notiphier.cfg")
    with open(_config_file, 'r') as config_fp:
        _config = json.load(config_fp)


reload_config()
