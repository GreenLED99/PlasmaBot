import os
import shutil
from threading import Thread
import fnmatch
import collections

from ruamel.yaml import YAML


class ConfigException(Exception):
    """An Exception thrown when a config key does not exist in either the main or backup config files."""

    def __init__(self):
        Exception.__init__(self, 'Config Key Requested Does Not Exist.')


class Config(collections.MutableMapping):
    """A wrapper for the bot's YAML config file."""

    def __init__(self, client):
        self.client = client
        self.path = 'config/config.yaml'
        self.defaults = 'plasmaBot/defaults/config.yaml'

        self.yaml = YAML(typ='rt')
        self.yaml.preserve_quotes = True

        if not os.path.isfile(self.path):
            self.client.printer.warning('Config File Missing.  Copying Backup File to \'{}\'...'.format(self.path))

            try:
                shutil.copy(self.defaults, self.path)
                self.client.printer.success('Copy Success!  Please edit this file and restart the bot.', tag=2, cmd=False)
            except Exception:
                self.client.printer.warning('Backup File missing.  Please restore the backup file {} and restart the bot.'.format(self.defaults), tag=2, cmd=False)

            self.client.shutdown()

        self.config_files = self.__detect_config_files()

        self.config_dict = self.__reload_config()

        defaults_stream = open(self.defaults, 'r')
        self.defaults_dict = self.yaml.load(defaults_stream)
        defaults_stream.close()

    def __detect_config_files(self):
        root_directory = os.getcwd()
        config_directory = root_directory + '/config'

        config_files = []

        for root, dirnames, filenames in os.walk(config_directory):
            for filename in fnmatch.filter(filenames, 'config.yaml'):
                config_files.append(os.path.join(root, filename))

        return map(lambda f: (f, os.stat(f).st_mtime), config_files)

    def __poll_config_changes(self):
        new_config_files = self.__detect_config_files()
        if self.config_files != new_config_files:
            self.config_files = new_config_files
            return True
        else:
            return False

    def __reload_config(self):
        config_stream = open(self.path, 'r')
        self.config_dict = self.yaml.load(config_stream)
        config_stream.close()

    def __getitem__(self, key):
        if self.__poll_config_changes():
            self.__reload_config()

        if key in self.config_dict:
            return self.config_dict[key]
        elif key in self.defaults_dict:
            return self.defaults_dict[key]
        else:
            raise ConfigException

    def __setitem__(self, key, item):
        if self.__poll_config_changes():
            self.__reload_config()

        self.config_dict[key] = item

        config_stream = open(self.path, 'w')
        config_stream.truncate()
        self.yaml.dump(self.config_dict, config_stream)
        config_stream.close()

        self.config_files = self.__detect_config_files()

    def __len__(self):
        return len(self.config_dict)

    def __delitem__(self, key):
        if self.__poll_config_changes():
            self.__reload_config()

        del self.config_dict[key]

        config_stream = open(self.path, 'w')
        config_stream.truncate()
        self.yaml.dump(self.config_dict, config_stream)
        config_stream.close()

    def clear(self):
        self.config_dict.clear()

        config_stream = open(self.path, 'w')
        config_stream.truncate()
        self.yaml.dump(self.config_dict, config_stream)
        config_stream.close()

    def keys(self):
        return self.config_dict.keys()

    def values(self):
        return self.config_dict.values()

    def items(self):
        return self.config_dict.items()

    def __contains__(self, item):
        return item in self.config_dict

    def __iter__(self):
        return iter(self.config_dict)
