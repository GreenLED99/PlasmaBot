"""PLASMABOT PLUGIN CLASS"""

def command(handler, cmd_type, *, description='None', usage='None', hidden=False, private=True, permission=None):
    """Signifies a plugin method as representing a command."""
    def command_decorator(command_method):
        """Decorator function that applies neccesary information to command_method as attributes."""
        command_method.handler = str(handler).lower().strip().split()[0]
        command_method.cmd_type = int(cmd_type) if int(cmd_type) in [0, 1, 2] else None
        command_method.description = str(description)
        command_method.usage = str(usage)
        command_method.hidden = bool(hidden) if command_method.cmd_type == 0 else False
        command_method.private = bool(private) if command_method.cmd_type == 0 else False
        command_method.permission = str(permission).split(',')[0].strip()

        if (command_method.cmd_type != None) and (command_method.handler != ''):
            command_method.command = True

        return command_method
    return command_decorator


def event(event_method):
    """Decorator that marks a plugin method as an plugin event hook."""
    event_method.event = True
    return event_method


class ChannelResponse(object):
    """A Response to a given channel command."""
    def __init__(self, *, content=None, embed=None, file=None, expire=30, send_help=False, mentions=False):
        if send_help:
            self.send_help = True
            self.content = None
            self.file = None
            self.embed = None
            self.expire = expire
        else:
            self.send_help = False
            self.content = content.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere') if not (content == None or mentions) else content
            self.file = file
            self.embed = embed
            self.expire = expire


class TerminalResponse(object):
    """A Response to a given terminal command."""
    def __init__(self, *, content=None, send_help=False):
        self.content = content if not send_help else None
        self.send_help = send_help


class ConfigResponse(object):
    """A Response to a given configuration command."""
    def __init__(self, *, content=None, send_help=False):
        self.content = content if not send_help else None
        self.send_help = send_help


class PluginMeta(type):
    """Metaclass to construct Plugin Class.  Registers Plugins in list for easier tracking."""
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, 'all'):
            cls.all = []
        else:
            cls.all += [cls]


class Plugin(object, metaclass=PluginMeta):
    """Plugin that provides and extends bot functionality through the use of command and event methods."""

    NAME = 'Generic'
    GUILD_BLACKLIST = []
    CHANNEL_BLACKLIST = []
    GUILD_WHITELIST = []
    CHANNEL_WHITELIST = []
    ENABLED = True

    def __init__(self, client):
        self.client = client
        self.config = client.config
        self.printer = client.printer
        self.permissions = client.permissions
        self.terminal = client.terminal
        self.on_plugin_load()

    def filter_mentions(self, string):
        """Method to filter mentions from a given string"""
        return string.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')

    def on_plugin_load(self):
        """Event fired on plugin load.  Designed for initializing attributes neccesary for plugin operation."""
        pass
