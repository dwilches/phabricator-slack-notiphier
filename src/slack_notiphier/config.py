
import yaml
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


def reload():
    global _config, _config_file
    _config_file = os.getenv('NOTIPHIER_CONFIG_FILE', "/etc/slack-notiphier.cfg")
    with open(_config_file, 'r') as config_fp:
        _config = yaml.load(config_fp)

    if 'channels' not in _config:
        raise KeyError('Need a channels element in the config file.')

    if '__default__' not in _config['channels']:
        raise KeyError('Need to specify a default channels in the config file.')


reload()
