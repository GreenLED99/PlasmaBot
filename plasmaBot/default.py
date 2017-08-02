"""DEFAULT PLASMABOT PLUGIN"""

from plasmaBot.plugin import Plugin, ChannelResponse, TerminalResponse, command, event
import datetime
import discord
import difflib

class Default(Plugin):
    """The main, default PlasmaBot Plugin with standard commands and functionality"""

    NAME = 'Main'

    @command('shutdown', 0, description='Shutdown the Bot Client', usage='shutdown', hidden=True, permission='owner')
    async def channel_shutdown(self, channel):
        """Shutdown Command: Shut the bot client down from within Discord"""
        await channel.send('Shutting Down...')
        self.client.shutdown()

    @command('shutdown', 1, description='Shutdown the Bot Client', usage='shutdown')
    async def terminal_shutdown(self, channel):
        """Shutdown Command: Shut the bot client down from the terminal interface"""
        self.client.shutdown()

    @command('restart', 0, description='Restart the Bot Client', usage='restart', hidden=True, permission='owner')
    async def channel_restart(self, channel):
        """Shutdown Command: Restart the bot client down from within Discord"""
        await channel.send('Restarting...')
        self.client.restart()

    @command('restart', 1, description='Restart the Bot Client', usage='restart')
    async def terminal_restart(self, channel):
        """Shutdown Command: Restart the bot client down from the terminal"""
        self.client.restart()

    @command('ping', 0, description='Test the status of the bot', usage='ping')
    async def ping(self, message, channel):
        """Ping Command: Test the status of the bot"""
        ping_msg = await channel.send(content='Pong!', delete_after=20)
        respond_time = ping_msg.created_at
        request_time = message.created_at
        difference = (respond_time - request_time).total_seconds()
        await ping_msg.edit(content='Pong! `{0:.2f}s`'.format(difference))

    @command('invite', 0, description='Get an Invite Link to invite the bot to your own server!', usage='invite')
    async def channel_invite(self, author):
        """Channel Invite Command: Provide the user with an invite link to invite the bot to their own servers"""
        if self.config['permissions']['invites'] or self.permissions.is_owner(author):
            application_info = await self.client.application_info()
            client_id = application_info.id

            permissions = discord.Permissions()
            permissions.administrator = True
            permissions.manage_channels = True
            permissions.manage_guild = True
            permissions.read_messages = True
            permissions.send_messages = True
            permissions.kick_members = True
            permissions.ban_members = True
            permissions.mute_members = True
            permissions.deafen_members = True
            permissions.manage_nicknames = True
            permissions.connect = True
            permissions.speak = True

            oauth_url = discord.utils.oauth_url(client_id, permissions)

            return ChannelResponse(content='Invite {} to your server! <{}>'.format(self.config['presence']['name'], oauth_url))

    @command('invite', 1, description='Generate an Invite Link to add the bot to a server', usage='invite')
    async def terminal_invite(self):
        """Terminal Invite Command: Provide the user with an invite link to invite the bot to their own servers"""
        application_info = await self.client.application_info()
        client_id = application_info.id

        permissions = discord.Permissions()
        permissions.administrator = True
        permissions.manage_channels = True
        permissions.manage_guild = True
        permissions.read_messages = True
        permissions.send_messages = True
        permissions.kick_members = True
        permissions.ban_members = True
        permissions.mute_members = True
        permissions.deafen_members = True
        permissions.manage_nicknames = True
        permissions.connect = True
        permissions.speak = True

        oauth_url = discord.utils.oauth_url(client_id, permissions)

        return TerminalResponse(content='{} Invite URL: {}'.format(self.config['presence']['name'], oauth_url))

    @command('id', 0, description='Get your ID!', usage='id')
    async def channel_id(self, author):
        """ID Command: Gets the ID of a user in a Discord Channel"""
        return ChannelResponse(content='{}, Your ID is `{}`'.format(author.mention, author.id))

    @command('verify', 0, description='Verify the current user\'s status', usage='verify', permission='owner')
    async def verify(self, author):
        """Verify Command: Used to verify Bot Owners from within a Discord Channel"""
        if author.id == 180094452860321793:
            return ChannelResponse(content='`VERIFICATION` {} is verified as a `Bot Developer`'.format(author.mention))
        else:
            return ChannelResponse(content='`VERIFICATION` {} is verified as a `Bot Owner`'.format(author.mention))

    @command('message', 1, description='Enable or Disable channel messaging through the terminal', usage='message')
    async def terminal_message(self):
        """Terminal Message Command:  Enable or Disable messaging through the terminal"""
        terminal = self.config['terminal']

        if terminal['messaging']:
            terminal['messaging'] = False
            if self.terminal.channel:
                self.printer.warning('Terminal Messaging Disabled. Disconnected from {}'.format('#{} in {}'.format(self.terminal.channel.name, self.terminal.guild.name) if self.terminal.guild else 'Direct Message with {}'.format(self.terminal.channel.recipient.display_name)))
            else:
                self.printer.warning('Terminal Messaging Disabled.')
        else:
            terminal['messaging'] = True

        self.config['terminal'] = terminal
        await self.terminal.detect_channel()

    @command('channel', 1, description='Switch the attached channel used for terminal messaging', usage='channel [#name|id|None]')
    async def terminal_channel(self, args):
        """Terminal Channel Command: Switch the attached channel used for terminal messaging"""
        if len(args) == 0:
            if self.terminal.guild:
                channel_string = ''
                for channel in self.terminal.guild.text_channels:
                    channel_string += '\n       - #{} ({})'.format(channel.name, channel.id)
                return TerminalResponse(content='{}Text Channels in {}:{}{}'.format(self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.terminal.guild.name, self.printer.Style.RESET_ALL, channel_string))
            else:
                dm_string = ''
                if len(self.client.private_channels) == 0:
                    dm_string = '\n       - None Found!'
                else:
                    for direct in self.client.private_channels:
                        dm_string += '\n       - #{} ({})'.format(direct.recipient.name, direct.id)
                return TerminalResponse(content='{}{}\'s Direct Messages:{}{}'.format(self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.config['presence']['name'], self.printer.Style.RESET_ALL, dm_string))
        elif len(args) == 1:
            channel = None
            if args[0] == 'direct':
                dm_string = ''
                if len(self.client.private_channels) == 0:
                    dm_string = '\n       - None Found!'
                else:
                    for direct in self.client.private_channels:
                        dm_string += '\n       - @{}#{} ({})'.format(direct.recipient.name, direct.recipient.discriminator, direct.id)
                return TerminalResponse(content='{}{}\'s Direct Messages:{}{}'.format(self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.config['presence']['name'], self.printer.Style.RESET_ALL, dm_string))
            elif args[0].isdigit():
                channel = self.client.get_channel(int(args[0]))

                if not channel:
                    channel = await self.client.get_user_info(int(args[0]))
            elif args[0].startswith('#'):
                if self.terminal.guild:
                    channel_names = [channel.name for channel in self.terminal.guild.text_channels]
                    closest_channel_names = difflib.get_close_matches(args[0][1:], channel_names, 10)
                    if len(closest_channel_names) >= 1:
                        channel_name = ''
                        for channel_match in closest_channel_names:
                            if channel_match.startswith(args[0][1]):
                                channel_name = channel_match
                                break
                        channel = discord.utils.get(self.terminal.guild.text_channels, name=channel_name)
                    else:
                        return TerminalResponse(content='Guild Channel Not Found')
                else:
                    return TerminalResponse(content='Channel Names Not Supported in Direct Messages')
            elif '#' in args[0]:
                if args[0].startswith('@'):
                    args[0] = args[0][1:]

                if self.terminal.guild:
                    user = self.terminal.guild.get_member_named(args[0])
                    if not user:
                        return TerminalResponse(content='No User Found in {}'.format(self.terminal.guild.name))
                else:
                    return TerminalResponse(content='Cannot lookup user by Discriminator and Username unless the Client is attached to a Guild.')
            else:
                if self.terminal.guild:
                    channel_names = [channel.name for channel in self.terminal.guild.text_channels]
                    closest_channel_names = difflib.get_close_matches(args[0], channel_names, 10)
                    if len(closest_channel_names) >= 1:
                        channel_name = ''
                        for channel_match in closest_channel_names:
                            if channel_match.startswith(args[0][0]):
                                channel_name = channel_match
                                break
                        channel = discord.utils.get(self.terminal.guild.text_channels, name=channel_name)
                    else:
                        return TerminalResponse(content='Guild Channel Not Found')
                else:
                    return TerminalResponse(content='Channel Names Not Supported in Direct Messages')

            if channel:
                terminal = self.config['terminal']
                terminal['channel'] = channel.id
                terminal['messaging'] = True
                self.config['terminal'] = terminal

                await self.terminal.detect_channel()
            else:
                return TerminalResponse(content='No Channel Found')
        else:
            return TerminalResponse(send_help=True)

    @command('guild', 1, description='Switch the attached channel to the primary channel of a given guild', usage='guild [name|ID|None]')
    async def terminal_guild(self, message, args):
        """Terminal Guild Command: Switch the attached channel to the primary channel of a given guild"""
        if len(args) == 0:
            guild_string = ''
            for guild in self.client.guilds:
                guild_string += '\n       - {} ({})'.format(guild.name, guild.id)
            return TerminalResponse(content='{}Connected Guilds for {}:{}{}'.format(self.printer.Back.BLACK + self.printer.Fore.MAGENTA, self.config['presence']['name'], self.printer.Style.RESET_ALL, guild_string))
        else:
            if args[0].isdigit():
                guild = self.client.get_guild(int(args[0]))
            else:
                guild_names = [guild.name for guild in self.client.guilds]
                closest_guild_names = difflib.get_close_matches(message[len(self.config['terminal']['prefix'] + 'guild '):], guild_names)
                if len(closest_guild_names) >= 1:
                    guild = discord.utils.get(self.client.guilds, name=closest_guild_names[0])
                else:
                    guild = None
            if guild:
                terminal = self.config['terminal']
                terminal['channel'] = sorted(guild.channels, key=lambda x: x.position)[0].id
                terminal['messaging'] = True
                self.config['terminal'] = terminal

                await self.terminal.detect_channel()
            else:
                return TerminalResponse(content='No Guild Found with this name.')

    @command('delete', 1, description='Delete a given message in the attached channel', usage='delete [ID|Index]')
    async def terminal_delete(self, args):
        """Terminal Delete:  Delete a given message in the attached channel."""
        if len(args) >= 1:
            if args[0].isdigit():
                try:
                    message = await self.terminal.channel.get_message(int(args[0]))
                    content = str(message.content)
                    author = str(message.author.name) + '#' + str(message.author.discriminator)
                    await message.delete()
                    return TerminalResponse(content='Successfully Deleted Message (Content: {}{}{}, Author: {})'.format(self.printer.Back.MAGENTA + self.printer.Fore.WHITE, content.replace('\n', '\n                '), self.printer.Style.RESET_ALL, author))
                except discord.Forbidden:
                    return TerminalResponse(content='Insufficient Permissions to Delete Message')
                except:
                    return TerminalResponse(content='Error Deleting Message')
            elif args[0].startswith('^'):
                index = args[0][1:]
                if not index.isdigit():
                    return TerminalResponse(content='Invalid Index: Not Integral')
                else:
                    index = int(index)

                messages = self.terminal.messages[self.terminal.channel.id]
                if index > len(messages):
                    return TerminalResponse(content='Invalid Index: Too High.')
                message = messages[-index]
                content = str(message.content)

                try:
                    await message.delete()
                    del self.terminal.messages[self.terminal.channel.id][len(messages) - index]
                    return TerminalResponse(content='Successfully Deleted Message (Content: {}{}{})'.format(self.printer.Back.MAGENTA + self.printer.Fore.WHITE, content.replace('\n', '\n                '), self.printer.Style.RESET_ALL))
                except discord.Forbidden:
                    return TerminalResponse(content='Insufficient Permissions to Delete Message')
                except:
                    return TerminalResponse(content='Error Deleting Message')
            else:
                return TerminalResponse(send_help=True)
        else:
            try:
                content = str(self.terminal.messages[self.terminal.channel.id][-1].content)
                await self.terminal.messages[self.terminal.channel.id][-1].delete()
                del self.terminal.messages[self.terminal.channel.id][-1]
                return TerminalResponse(content='Successfully Deleted Message (Content: {}{}{})'.format(self.printer.Back.MAGENTA + self.printer.Fore.WHITE, content.replace('\n', '\n                '), self.printer.Style.RESET_ALL))
            except discord.Forbidden:
                return TerminalResponse(content='Insufficient Permissions to Delete Message')
            except:
                return TerminalResponse(content='Error Deleting Message')

    @command('edit', 1, description='Edit the most recent message sent via the terminal interface in the current channel', usage='edit [new_content]')
    async def terminal_edit(self, message):
        """Terminal Edit Command:  Edit the most recent mesasge sent via the terminal interface"""
        last_message = self.terminal.messages[self.terminal.channel.id][-1]
        new_message = message[len(self.config['presence']['prefix'] + 'edit '):]
        await last_message.edit(content=new_message)
        return TerminalResponse(content='Message Edited')
