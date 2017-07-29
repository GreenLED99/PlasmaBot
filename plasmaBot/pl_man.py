"""PLASMABOT PLUGIN MANAGER"""

from SQLiteHelper import SQLiteHelper as sq
import asyncio
import inspect
import traceback
import datetime

import discord

from plasmaBot.defaults.tbl_presets import DBT_COMMANDS, DBT_PLUGINS, DBT_EVENTS
from plasmaBot.utils import Shutdown, Restart
from plasmaBot.plugin import *
from plasmaBot.default import *
from plugins import *

class PluginManager(object):
    """Class that handles the loading of plugins and the proper distribution of events"""
    def __init__(self, client):
        self.client = client
        self.config = client.config
        self.permissions = client.permissions
        self.logger = client.logger
        self.printer = client.printer
        self.terminal = client.terminal
        self.plugins = {}

        self.db = sq.Connect('plasmaBot/data/plugins')
        self.conn = self.db.getConn()
        self.cursor = self.conn.cursor()

        self.cursor.execute('DROP TABLE IF EXISTS commands_last_instance')
        self.cursor.execute('DROP TABLE IF EXISTS plugins_last_instance')
        self.cursor.execute('DROP TABLE IF EXISTS events_last_instance')

        if self.db.table('commands').tableExists():
            self.cursor.execute('ALTER TABLE commands RENAME TO commands_last_instance')

        if self.db.table('plugins').tableExists():
            self.cursor.execute('ALTER TABLE plugins RENAME TO plugins_last_instance')

        if self.db.table('events').tableExists():
            self.cursor.execute('ALTER TABLE events RENAME TO events_last_instance')

        self.db.table('commands').init(DBT_COMMANDS)
        self.db.table('plugins').init(DBT_PLUGINS)
        self.db.table('events').init(DBT_EVENTS)

    def load_all(self):
        """Load all plugins residing in the plugins folder."""
        self.plugins = {}

        for plugin_class in Plugin.all:
            self.load(plugin_class)

    def load(self, plugin):
        """Load an individual plugin class and initialize it."""

        already_loaded = self.db.table('plugins').select('CLASS_NAME').where('CLASS_NAME').equals(plugin.__name__).execute()
        duplicate = False
        empty = True

        for entry in already_loaded:
            duplicate = True

        if not duplicate:
            for attr_name, attr_obj in plugin.__dict__.items():
                if hasattr(attr_obj, 'command'):
                    if not attr_obj.cmd_type is None:
                        empty = False
                        self.db.table('commands').insert(attr_obj.handler, plugin.__name__, attr_name, attr_obj.cmd_type, attr_obj.description, attr_obj.usage, int(attr_obj.hidden), int(attr_obj.private), attr_obj.permission).into('HANDLER', 'PLUGIN', 'METHOD_NAME', 'TYPE', 'DESCRIPTION', 'USAGE', 'HIDDEN', 'PRIVATE', 'PERMISSION')
                elif hasattr(attr_obj, 'event'):
                    empty = False
                    self.db.table('events').insert(attr_name.lower(), plugin.__name__).into('EVENT_NAME', 'PLUGIN')

        if not empty:
            g_whitelist = ','.join(map(str, plugin.GUILD_WHITELIST))
            c_whitelist = ','.join(map(str, plugin.CHANNEL_WHITELIST))
            g_blacklist = ','.join(map(str, plugin.GUILD_BLACKLIST))
            c_blacklist = ','.join(map(str, plugin.CHANNEL_BLACKLIST))
            self.db.table('plugins').insert(plugin.__name__, str(plugin.NAME), int(plugin.ENABLED), g_whitelist, c_whitelist, g_blacklist, c_blacklist).into('CLASS_NAME', 'FANCY_NAME', 'ENABLED', 'G_WHITELIST', 'C_WHITELIST', 'G_BLACKLIST', 'C_BLACKLIST')

            self.plugins[plugin.__name__] = plugin(self.client)

    async def channel_help_command(self, channel, user, command=None):
        """Help Command for looking up bot commands within a Discord Channel"""
        if command:
            async with channel.typing():
                await asyncio.sleep(0.025)
                self.cursor.execute('SELECT * FROM commands WHERE TYPE=0 AND HANDLER=?', [command])
                cmd_return = self.cursor.fetchone()

                if not cmd_return:
                    await channel.send(content='Invalid Command!', delete_after=60, reason='Help Message Automatic Deletion')
                    return

                description = cmd_return[4]
                usage = cmd_return[5]
                hidden = bool(cmd_return[6])
                permission = cmd_return[8]

                if hidden:
                    await channel.send(content='Invalid Command!', delete_after=60, reason='Help Message Automatic Deletion')
                    return

                if not self.permissions.get_permission(permission, user, channel):
                    await channel.send(content='Invalid Permissions for this Command!', delete_after=60, reason='Help Message Automatic Deletion')
                    return

                help_embed = discord.Embed(title='Command Usage for `{}{}`:'.format(self.config['presence']['prefix'], command), color=discord.Colour.red()).set_footer(text='Requested by {}'.format(user.display_name), icon_url=user.avatar_url).add_field(name='Command Description', value=description, inline=False).add_field(name='Usage', value='{}{}'.format(self.config['presence']['prefix'], usage), inline=False)
                await channel.send(embed=help_embed, delete_after=60, reason='Help Message Automatic Deletion')
                return
        else:
            async with channel.typing():
                await asyncio.sleep(0.025)

                prefix = self.config['presence']['prefix']
                help_embed = discord.Embed(title='{} Commands'.format(self.config['presence']['name']), color=discord.Colour.purple())

                commands_return = self.db.table('commands').select('HANDLER', 'PLUGIN', 'DESCRIPTION', 'HIDDEN', 'PRIVATE', 'PERMISSION').where('TYPE').equals(0).execute()
                plugin_sorted = {}

                for command in commands_return:
                    command_str = '{}{} - {}'.format(prefix, command[0], command[2])
                    hidden = bool(command[3])
                    private = bool(command[4])
                    permission = command[5]

                    if not hidden and (private or not isinstance(channel, discord.abc.PrivateChannel)) and self.permissions.get_permission(permission, user, channel):
                        if not command[1] in plugin_sorted:
                            plugin_sorted[command[1]] = []
                        plugin_sorted[command[1]] += [command_str]

                for class_name, commands in plugin_sorted.items():
                    plugin_return = self.db.table('plugins').select('FANCY_NAME').where('CLASS_NAME').equals(class_name).execute()
                    fancy_name = class_name
                    for plugin in plugin_return:
                        fancy_name = plugin[0]

                    plugin_command_string = ''
                    for command_info in commands:
                        plugin_command_string += command_info + '\n'
                    plugin_command_string[:-1]

                    help_embed.add_field(name='{} Plugin:'.format(fancy_name), value=plugin_command_string, inline=False)

                help_embed.set_footer(text='Requested by {}'.format(user.display_name), icon_url=user.avatar_url)\

                await channel.send(embed=help_embed, delete_after=60, reason='Help Message Automatic Deletion')

    async def fire_channel_command(self, message): #integrate blacklist and permission checks
        """Channel Command Event Distributer, calls required command events in the desired plugin."""
        if self.permissions.is_blacklisted(message.author, message.channel) or message.author == self.client.user:
            return

        prefix = self.config['presence']['prefix']

        if not message.content.startswith(prefix):
            return

        handler, *args = message.content.strip()[len(prefix):].split()
        arg_content = message.content.strip()[len(prefix + handler + ' '):]

        handler = handler.lower()
        private_channel = isinstance(message.channel, discord.abc.PrivateChannel)

        if message.content.startswith(prefix + 'help'):
            if len(args) >= 1:
                await self.channel_help_command(message.channel, message.author, args[0])
                return
            else:
                await self.channel_help_command(message.channel, message.author)
                return

        self.cursor.execute('SELECT * FROM commands WHERE TYPE=0 AND HANDLER=?', [handler.strip()])
        cmd_return = self.cursor.fetchone()

        if not cmd_return:
            return

        plugin_name = cmd_return[1]
        method_name = cmd_return[2]
        description = cmd_return[4]
        usage = cmd_return[5]
        hidden = bool(cmd_return[6])
        no_private = not bool(cmd_return[7])
        permission = cmd_return[8]

        silence_errors = True if (self.config['commands']['mute-hidden'] and hidden) else False

        self.cursor.execute('SELECT * FROM plugins WHERE CLASS_NAME =?;', [plugin_name])
        plugin_return = self.cursor.fetchone()

        if not plugin_return:
            return

        fancy_plugin = plugin_return[1]
        enabled = bool(plugin_return[2])

        if not enabled:
            return

        if not plugin_return[3] == '':
            g_whitelist = [int(id_item) for id_item in plugin_return[3].split(',')]
        else:
            g_whitelist = []

        if not plugin_return[5] == '':
            g_blacklist = [int(id_item) for id_item in plugin_return[5].split(',')] if not g_whitelist else []
        else:
            g_blacklist = []

        if not plugin_return[4] == '':
            c_whitelist = [int(id_item) for id_item in plugin_return[4].split(',')]
        else:
            c_whitelist = []

        if not plugin_return[6] == '':
            c_blacklist = [int(id_item) for id_item in plugin_return[6].split(',')] if not c_whitelist else []
        else:
            c_blacklist = []

        if isinstance(message.channel, discord.abc.GuildChannel):
            if message.channel.guild.id in g_blacklist or message.channel.id in c_blacklist or not enabled:
                return

            if g_whitelist and not message.channel.guild.id in g_whitelist:
                if c_whitelist and not message.channel.id in c_whitelist:
                    return
                elif message.channel.id in c_blacklist:
                    return
            elif c_whitelist and not message.channel.id in c_whitelist:
                return

        method = getattr(self.plugins[plugin_name], method_name)

        if not method:
            self.printer.error('[CMD] Command Handler Not Found')
            return

        with message.channel.typing():
            if no_private and private_channel:
                if not silence_errors:
                    await message.channel.send('**Command *`{}`* is not enabled in Direct Messages**')
                return

            if not self.permissions.get_permission(permission, message.author, message.channel):
                if not silence_errors:
                    await message.channel.send('**INVALID Permissions**: {} does not have the `{}` permission.'.format(message.author.display_name, permission), reason='Help Message Automatic Deletion')
                return

            argspec = inspect.signature(method)
            params = argspec.parameters.copy()

            try:
                method_kwargs = {}

                if params.pop('message', None):
                    method_kwargs['message'] = message

                if params.pop('content', None):
                    method_kwargs['content'] = message.content[len(prefix + handler + ' '):].strip()

                if params.pop('channel', None):
                    method_kwargs['channel'] = message.channel

                if params.pop('author', None):
                    method_kwargs['author'] = message.author

                if params.pop('guild', None):
                    if isinstance(message.channel, discord.abc.PrivateChannel):
                        method_kwargs['guild'] = None
                    else:
                        method_kwargs['guild'] = message.guild

                if params.pop('guild_member', None):
                    if isinstance(message.channel, discord.abc.PrivateChannel):
                        method_kwargs['guild_member'] = None
                    else:
                        method_kwargs['guild_member'] = message.guild.me

                if params.pop('user_mentions', None):
                    method_kwargs['user_mentions'] = message.mentions

                if params.pop('channel_mentions', None):
                    method_kwargs['channel_mentions'] = message.channel_mentions

                if params.pop('role_mentions', None):
                    method_kwargs['role_mentions'] = message.role_mentions

                if params.pop('args', None):
                    method_kwargs['args'] = list(args)

                for key, param in list(params.items()):
                    if not args and param.default is not inspect.Parameter.empty:
                        params.pop(key)
                        continue

                    if args:
                        arg_value = args.pop(0)
                        method_kwargs[key] = arg_value
                        params.pop(key)

                if params:
                    help_embed = discord.Embed(title='Command Usage for `{}{}` ({} Plugin):'.format(prefix, handler.strip(), fancy_plugin), color=discord.Colour.red()).set_footer(text='Requested by {}'.format(message.author.display_name), icon_url=message.author.avatar_url).add_field(name='Command Description', value=description, inline=False).add_field(name='Usage', value='{}{}'.format(prefix, usage), inline=False)

                    await message.channel.send(embed=help_embed, delete_after=30, reason='Help Message Automatic Deletion')
                    return

                await asyncio.sleep(0.075)

                response = await method(**method_kwargs)

                if response and isinstance(response, ChannelResponse):
                    if response.send_help:
                        help_embed = discord.Embed(title='Command Usage for `{}{}` ({} Plugin):'.format(prefix, handler.strip(), fancy_plugin), color=discord.Colour.red()).set_footer(text='Requested by {}'.format(message.author.display_name), icon_url=message.author.avatar_url).add_field(name='Command Description', value=description, inline=False).add_field(name='Usage', value='{}{}'.format(prefix, usage), inline=False)

                        await message.channel.send(embed=help_embed, delete_after=response.expire, reason='Help Message Automatic Deletion')
                        return
                    else:
                        await message.channel.send(response.content, embed=response.embed, file=response.file, delete_after=response.expire, reason='Bot Response Automatic Deletion')
            except Shutdown or Restart:
                raise
            except Exception:
                await self.logger.error(message.author, message.channel, message.content, traceback.format_exc())

    async def terminal_help_command(self, command=None):
        """Help Command for looking up commands from within the terminal interface"""
        if command:
            self.cursor.execute('SELECT * FROM commands WHERE TYPE=1 AND HANDLER=?', [command])
            cmd_return = self.cursor.fetchone()

            if not cmd_return:
                self.printer.warning('Invalid Command!')
                return

            description = cmd_return[4]
            usage = cmd_return[5]
            hidden = bool(cmd_return[6])
            permission = cmd_return[8]

            if hidden:
                self.printer.warning('Invalid Command!')
                return

            self.printer.indicate('{4}Command Usage for "{0}{1}"{5}\n      {4}Description:{5} {2}\n      {4}Usage:{5} {3}\n'.format(self.config['terminal']['prefix'], command, description, usage, self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.printer.Style.RESET_ALL))
            return
        else:
            prefix = self.config['terminal']['prefix']
            help_message = '{}{} Terminal Commands{}'.format(self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.config['presence']['name'], self.printer.Style.RESET_ALL)

            commands_return = self.db.table('commands').select('HANDLER', 'PLUGIN', 'DESCRIPTION', 'HIDDEN', 'PRIVATE', 'PERMISSION').where('TYPE').equals(1).execute()
            plugin_sorted = {}

            plugin_string = ''

            for command in commands_return:
                command_str = '       * {}{} - {}'.format(prefix, command[0], command[2])
                hidden = bool(command[3])
                private = bool(command[4])
                permission = command[5]

                if not hidden and (private or not isinstance(self.terminal.channel, discord.abc.PrivateChannel)):
                    if not command[1] in plugin_sorted:
                        plugin_sorted[command[1]] = []
                    plugin_sorted[command[1]] += [command_str]

            for class_name, commands in plugin_sorted.items():
                plugin_return = self.db.table('plugins').select('FANCY_NAME').where('CLASS_NAME').equals(class_name).execute()
                fancy_name = class_name
                for plugin in plugin_return:
                    fancy_name = plugin[0]

                plugin_command_string = ''
                for command_info in commands:
                    plugin_command_string += '\n' + command_info

                plugin_string += '\n      {} Plugin:{}'.format(fancy_name, plugin_command_string)

            help_message += plugin_string
            self.printer.indicate(help_message)
            return

    async def fire_terminal_command(self, message):
        """Terminal Command Event Distributer, calls desired commands in their respective plugins."""

        prefix = self.config['terminal']['prefix']

        handler, *args = message.strip()[len(prefix):].split()
        handler = handler.lower().strip()

        if message.startswith(prefix + 'help'):
            if len(args) >= 1:
                await self.terminal_help_command(args[0])
                return
            else:
                await self.terminal_help_command()
                return

        self.cursor.execute('SELECT * FROM commands WHERE TYPE=1 AND HANDLER=?', [handler])
        cmd_return = self.cursor.fetchone()

        if not cmd_return:
            self.printer.warning('Invalid Terminal Command.')
            return

        plugin_name = cmd_return[1]
        method_name = cmd_return[2]
        description = cmd_return[4]
        usage = cmd_return[5]
        hidden = bool(cmd_return[6])
        no_private = not bool(cmd_return[7])
        permission = cmd_return[8]

        self.cursor.execute('SELECT * FROM plugins WHERE CLASS_NAME =?;', [plugin_name])
        plugin_return = self.cursor.fetchone()

        if no_private and isinstance(self.terminal.channel, discord.abc.PrivateChannel):
            self.printer.warning('Command Disabled while attached to Direct Message.')

        if not plugin_return:
            self.printer.warning('Invalid Terminal Command.')
            return

        fancy_plugin = plugin_return[1]
        enabled = bool(plugin_return[2])

        if not enabled:
            self.printer.warning('Invalid Terminal Command.')
            return

        method = getattr(self.plugins[plugin_name], method_name)

        argspec = inspect.signature(method)
        params = argspec.parameters.copy()

        try:
            method_kwargs = {}

            if params.pop('message', None):
                method_kwargs['message'] = message

            if params.pop('channel', None):
                method_kwargs['channel'] = self.terminal.channel

            if params.pop('guild', None):
                method_kwargs['guild'] = self.terminal.guild

            if params.pop('guild_member', None):
                method_kwargs['guild_member'] = self.terminal.guild_member

            if params.pop('datetime', None):
                method_kwargs['datetime'] = datetime.datetime.utcnow()

            if params.pop('user_mentions', None):
                mentions = []
                if self.terminal.guild:
                    for argument in list(args):
                        id_member = self.terminal.guild.get_member(argument[1:] if argument.startswith('@') else argument)
                        if id_member:
                            mentions += [id_member]
                        elif argument.startswith('@'):
                            name_member = self.terminal.guild.get_member_named(argument[1:])
                            if name_member:
                                mentions += [name_member]
                else:
                    if '{}'.format(self.channel.recipient.id) in args or '@{}'.format(self.channel.recipient.id) in list(args) or '@{}'.format(self.channel.recipient.display_name) in list(args):
                        mentions = [self.channel.recipient]

                method_kwargs['user_mentions'] = mentions

            if params.pop('role_mentions', None):
                if not self.terminal.guild:
                    method_kwargs['role_mentions'] = []
                else:
                    mentions = []
                    for role in self.terminal.guild.roles:
                        if role.id in args or '@{}'.format(role.id) in args or '@{}'.format(role.name) in args:
                            mentions += [role]

                    method_kwargs['role_mentions'] = mentions

            if params.pop('channel_mentions', None):
                if not self.terminal.guild:
                    method_kwargs['channel_mentions'] = []
                else:
                    mentions = []
                    for channel in self.terminal.guild.text_channels:
                        if channel.id in args or '@{}'.format(channel.id) in args or '@{}'.format(channel.name) in args:
                            mentions += [channel]

                    method_kwargs['channel_mentions'] = mentions

            if params.pop('args', None):
                method_kwargs['args'] = list(args)

            for key, param in list(params.items()):
                if not args and param.default is not inspect.Parameter.empty:
                    params.pop(key)
                    continue

                if args:
                    arg_value = args.pop(0)
                    method_kwargs[key] = arg_value
                    params.pop(key)

            if params:
                self.printer.indicate('{5}Command Usage for `{0}{1}` ({2} Plugin){6}\n      {5}Description:{6} {3}\n      {5}Usage:{6} {4}\n'.format(prefix, handler, fancy_plugin, description, usage, self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.printer.Style.RESET_ALL))
                return

            response = await method(**method_kwargs)

            if response and isinstance(response, TerminalResponse):
                if response.send_help:
                    self.printer.indicate('{5}Command Usage for `{0}{1}` ({2} Plugin){6}\n      {5}Description:{6} {3}\n      {5}Usage:{6} {4}\n'.format(prefix, handler, fancy_plugin, description, usage, self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.printer.Style.RESET_ALL))
                    return
                else:
                    self.printer.indicate(response.content)

        except (Shutdown, Restart):
            raise

        except:
            self.printer.warning('Ignoring Traceback in Terminal Command \'{}\'\n{}'.format(message, traceback.format_exc()))

    async def run_event(self, event_name, *args, **kwargs):
        """Method for bubbling client events to plugin event handlers"""
        if event_name.lower() == 'on_message':
            await self.fire_channel_command(*args, **kwargs)

        event_return = self.db.table('events').select('PLUGIN').where('EVENT_NAME').equals(event_name.lower()).execute()

        for plugin in event_return:
            await getattr(self.plugins[plugin[0]], event_name)(*args, **kwargs)
