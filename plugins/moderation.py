"""MODERATION PLUGIN"""

from plasmaBot.plugin import Plugin, ChannelResponse, command

from SQLiteHelper import SQLiteHelper as sq
from plasmaBot.utils import databaseTable

import discord
import asyncio

GUILD_DEFAULTS = databaseTable(['GUILD_ID', 'LOG_CHANNEL', 'STATIC_CHANNELS'],
                               ['INT PRIMARY KEY NOT NULL', 'INT DEFAULT 0', 'STR DEFAULT ""'])


class Moderation(Plugin):
    """A Client Plugin that handles functionality vital to the moderation of servers"""

    NAME = 'Moderation'

    def on_plugin_load(self):
        """Event fired on plugin load.  Initializes Plugin elements."""
        self.db = sq.Connect('plasmaBot/data/moderation')

        if not self.db.table('guilds').tableExists():
            self.db.table('guilds').init(GUILD_DEFAULTS)

        self.permissions.register('manage_logs', False, 'Moderation')
        self.permissions.register('text_mute_members', False, 'Moderation')
        self.permissions.register('text_deafen_members', False, 'Moderation')

    def get_log_channel(self, guild):
        """Method that queries the database for the log channel in a given guild"""
        guild_return = self.db.table('guilds').select('LOG_CHANNEL').where('GUILD_ID').equals(guild.id).execute()
        channel_id = None

        for index in guild_return:
            channel_id = int(index[0])

        if not channel_id:
            return None

        return discord.utils.get(self.client.get_all_channels(), id=channel_id)

    def set_log_channel(self, channel, guild):
        """Set the log channel for a given guild"""
        current_channel = self.get_log_channel(guild)

        if not current_channel:
            self.db.table('guilds').insert(guild.id, channel.id).into('GUILD_ID', 'LOG_CHANNEL')
        else:
            self.db.table('guilds').update('LOG_CHANNEL').setTo(channel.id).where('GUILD_ID').equals(guild.id).execute()

    def remove_log_channel(self, guild):
        """Remove a moderation log channel for a given guild"""
        self.db.table('guilds').delete().where('GUILD_ID').equals(guild.id).execute()

    def query_log_channel(self, guild):
        """Method that queries the log channel of a given server and returns an appropriate response"""
        channel = self.get_log_channel(guild)
        if channel:
            return ChannelResponse(content='Moderation Log Channel currently set to {} in {}'.format(channel.mention, guild.name))
        else:
            return ChannelResponse(content='No Moderation Log Channel set for {}'.format(guild.name))

    def get_static_channels(self, guild):
        """Method that gets a list of channel IDs that should be ignored by read-blocking moderation commands"""
        guild_return = self.db.table('guilds').select('STATIC_CHANNELS').where('GUILD_ID').equals(guild.id).execute()
        channel_ids = []

        for index in guild_return:
            if not index[0] == None:
                for channel_id in str(index[0]).split():
                    if channel_id.isdigit:
                        channel_ids += [int(channel_id)]

        return channel_ids

    def save_static_channels(self, guild, channel_list):
        """Method that saves a list of channel IDs to the moderation database"""
        db_string = ' '.join([str(channel_id) for channel_id in channel_list])

        guild_return = self.db.table('guilds').select('GUILD_ID').where('GUILD_ID').equals(guild.id).execute()
        entry_does_exist = False

        for index in guild_return:
            entry_does_exist = True

        if entry_does_exist:
            self.db.table('guilds').update('STATIC_CHANNELS').setTo(db_string).where('GUILD_ID').equals(guild.id).execute()
        else:
            self.db.table('guilds').insert(guild.id, db_string).into('GUILD_ID', 'STATIC_CHANNELS')

    def add_static_channel(self, channel):
        """Method that marks a channel ID as static to be ignored by read-blocking moderation commands"""
        if not isinstance(channel, discord.abc.GuildChannel):
            return

        channel_ids = self.get_static_channels(channel.guild)

        if not channel.id in channel_ids:
            channel_ids += [channel.id]

        self.save_static_channels(channel.guild, channel_ids)

    def remove_static_channel(self, channel):
        """Method that removes a channel ID from the list of static channels that are ignored by read-blocking moderation commands"""
        if not isinstance(channel, discord.abc.GuildChannel):
            return

        channel_ids = self.get_static_channels(channel.guild)

        if channel.id in channel_ids:
            channel_ids.remove(channel.id)

        self.save_static_channels(channel.guild, channel_ids)

    @command('modlog', 0, description='Set the channel to which moderation actions are logged', usage='modlog (channel|None)', permission='administrator manage_logs', private=False)
    async def modlog_command(self, guild, channel_mentions, args):
        """Command that sets the moderation log channel for the current server"""
        if not args:
            return self.query_log_channel(guild)

        if args[0].lower().strip() == 'none' and self.get_log_channel(guild):
            self.remove_log_channel(guild)
            return ChannelResponse(content='Moderation Log Channel removed for {}'.format(guild.name))

        if not channel_mentions:
            return ChannelResponse(send_help=True)

        if not args[0] == channel_mentions[0].mention:
            return ChannelResponse(send_help=True)

        self.set_log_channel(channel_mentions[0], guild)

        if not self.get_log_channel(guild) == channel_mentions[0]:
            return ChannelResponse(content='Error Setting Moderation Log Channel for {}'.format(guild.name))
        else:
            return ChannelResponse(content='Moderation Log Channel set to {} for {}'.format(channel_mentions[0].mention, guild.name))

    @command('ignore', 0, description='Mark channels or a channel to be ignored by read-blocking moderation comamnds', usage='ignore [add|remove] [channel] (channel)...', permission='administrator text_deafen_members jail_members', private=False)
    async def ignore_channel_command(self, guild, channel_mentions, args):
        """Mark channels or a channel to be ignored by read-blocking moderation comamnds"""
        if not args:
            ignored_channels = [guild.get_channel(channel_id) for channel_id in self.get_static_channels(guild)]
            ignored_channel_mentions = [' ' if not channel else channel.mention for channel in ignored_channels]
            return ChannelResponse(content='The following channels are ignored in {}: {}'.format(guild.name, ' '.join(ignored_channel_mentions)))

        if not len(args) >= 2:
            return ChannelResponse(send_help=True)

        if not len(channel_mentions) >= 1:
            return ChannelResponse(send_help=True)

        operation = args[0].strip().lower()

        if operation == channel_mentions[0].mention:
            return ChannelResponse(send_help=True)

        if not operation in ['add', 'remove']:
            return ChannelResponse(send_help=True)

        for channel in channel_mentions:
            if operation == 'add':
                self.add_static_channel(channel)
            else:
                self.remove_static_channel(channel)

        return ChannelResponse(content='Successfully {} the following channels {} the ignore list: {}'.format('added' if operation == 'add' else 'removed', 'to' if operation == 'add' else 'from', ' '.join([channel.mention for channel in channel_mentions])))

    @command('mute', 0, description='Prevent a guild member from sending messages to a given text channel', usage='mute [user] (channel) [reason]', permission='administrator text_mute_members', private=False)
    async def text_mute_command(self, author, channel, guild, content, user_mentions, channel_mentions, args):
        """Command that prevents a guild member from sending messages to a given text channel"""
        if not len(user_mentions) >= 1:
            return ChannelResponse(send_help=True)

        if not len(content) >= len(user_mentions[0].mention + ' '):
            reason = 'No Reason Provided'
        else:
            reason = content[len(user_mentions[0].mention + ' '):]

        user = user_mentions[0]

        if user == author:
            return ChannelResponse(content='*Muting one\'s self is rarely beneficial*')

        if self.permissions.has_any_permission(['administrator', 'text_mute_members'], user, channel):
            return ChannelResponse(content='*Member can not be muted due to elevated mute permissions*')

        channel_perms = self.permissions.has_any_permission(['administrator', 'text_mute_members'], author, channel)
        guild_perms = self.permissions.has_any_permission(['administrator', 'text_mute_members'], author, channel.guild)

        target = None

        if len(channel_mentions) >= 1:
            if args[1] == channel_mentions[0].mention:
                target = channel_mentions[0]
                target_perms = self.permissions.has_any_permission(['administrator', 'text_mute_members'], author, target)

                if not target.guild == guild:
                    return ChannelResponse(content='*Passed Channel must belong to the current Guild*')

                if not target_perms:
                    return ChannelResponse(content='**INVALID Permissions**: {} does not have the `administrator` or `text_mute_members` permission in {}.'.format(author.display_name, target.mention))

                if not len(reason) >= len(target.mention + ' '):
                    reason = 'No Reason Provided'
                else:
                    reason = reason[len(target.mention + ' '):]

        if (not target) and (not guild_perms):
            target = channel

        log_channel = self.get_log_channel(guild)

        if target:
            if not target.permissions_for(user).send_messages:
                return ChannelResponse(content='*{} is already devoid of messaging permissions in {}*'.format(user, target.mention))

            mute_message = await channel.send(content=self.filter_mentions('Muting {} in {}...'.format(user.display_name, target.mention)))

            try:
                await target.set_permissions(user, reason='TEXT-MUTE: {}'.format(reason), send_messages=False)
            except:
                await mute_message.edit(content=self.filter_mentions('Error Muting {} in {}.'.format(user.display_name, target.mention)))
                return

            await mute_message.edit(content=self.filter_mentions('Muted {} in {}.'.format(user.display_name, target.mention)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='MUTE: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                log_embed.add_field(name='Reason', value=reason, inline=False).add_field(name='Channel', value=target.mention, inline=False).add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

            await asyncio.sleep(10)
            await mute_message.delete()

            return
        else:
            mute_message = await channel.send(content=self.filter_mentions('Muting {}...'.format(user.display_name)))

            error_channels = []

            if channel.permissions_for(user).send_messages:
                try:
                    await channel.set_permissions(user, reason='TEXT-MUTE: {}'.format(reason), send_messages=False)
                except:
                    error_channels += [channel]

            for target in guild.text_channels:
                if target.permissions_for(user).send_messages and not channel == target:
                    try:
                        await target.set_permissions(user, reason='TEXT-MUTE: {}'.format(reason), send_messages=False)
                    except:
                        error_channels += [target]

            if error_channels:
                await mute_message.edit(content=self.filter_mentions('Unable to mute {} in {} of {} channels'.format(user, len(error_channels), len(guild.text_channels))))
            else:
                await mute_message.edit(content=self.filter_mentions('Muted {}...'.format(user.display_name)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='MUTE: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                log_embed.add_field(name='Reason', value=reason, inline=False).add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

            await asyncio.sleep(10)
            await mute_message.delete()

            return

    @command('unmute', 0, description='Return messaging permissions to a given guild member', usage='mute [user] (channel) [reason]', permission='administrator text_mute_members', private=False)
    async def text_unmute_command(self, author, channel, guild, content, user_mentions, channel_mentions, args):
        """Return messaging permissions to a given guild member"""
        if not len(user_mentions) >= 1:
            return ChannelResponse(send_help=True)

        if not len(content) >= len(user_mentions[0].mention + ' '):
            reason = None
        else:
            reason = content[len(user_mentions[0].mention + ' '):]

        user = user_mentions[0]

        channel_perms = self.permissions.has_any_permission(['administrator', 'text_mute_members'], author, channel)
        guild_perms = self.permissions.has_any_permission(['administrator', 'text_mute_members'], author, channel.guild)

        target = None

        if len(channel_mentions) >= 1:
            if args[1] == channel_mentions[0].mention:
                target = channel_mentions[0]
                target_perms = self.permissions.has_any_permission(['administrator', 'text_mute_members'], author, target)

                if not target.guild == guild:
                    return ChannelResponse(content='*Passed Channel must belong to the current Guild*')

                if not target_perms:
                    return ChannelResponse(content='**INVALID Permissions**: {} does not have the `administrator` or `text_mute_members` permission in {}.'.format(author.display_name, target.mention))

                if reason:
                    if not len(reason) >= len(target.mention + ' '):
                        reason = None
                    else:
                        reason = reason[len(target.mention + ' '):]

        if (not target) and (not guild_perms):
            target = channel

        log_channel = self.get_log_channel(guild)

        if target:
            if not target.permissions_for(user).send_messages == False:
                return ChannelResponse(content='*{} already has messaging permissions in {}*'.format(user, target.mention))

            mute_message = await channel.send(content=self.filter_mentions('Un-Muting {} in {}...'.format(user.display_name, target.mention)))

            try:
                await target.set_permissions(user, reason='REMOVE TEXT-MUTE: {}'.format(reason), send_messages=None)
            except:
                await mute_message.edit(content=self.filter_mentions('Error Un-Muting {} in {}.'.format(user.display_name, target.mention)))
                return

            await mute_message.edit(content=self.filter_mentions('Un-Muted {} in {}.'.format(user.display_name, target.mention)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='UN-MUTE: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                if reason:
                    log_embed.add_field(name='Reason', value=reason, inline=False)
                log_embed.add_field(name='Channel', value=target.mention, inline=False).add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

            await asyncio.sleep(10)
            await mute_message.delete()

            return
        else:
            mute_message = await channel.send(content=self.filter_mentions('Un-Muting {}...'.format(user.display_name)))

            error_channels = []

            if channel.permissions_for(user).send_messages == False:
                try:
                    await channel.set_permissions(user, reason='REMOVE TEXT-MUTE: {}'.format(reason), send_messages=None)
                except:
                    error_channels += [channel]

            for target in guild.text_channels:
                if target.permissions_for(user).send_messages == False and not channel == target:
                    try:
                        await target.set_permissions(user, reason='REMOVE TEXT-MUTE: {}'.format(reason), send_messages=None)
                    except:
                        error_channels += [target]

            if error_channels:
                await mute_message.edit(content=self.filter_mentions('Unable to un-mute {} in {} of {} channels'.format(user, len(error_channels), len(guild.text_channels))))
            else:
                await mute_message.edit(content=self.filter_mentions('Un-Muted {}...'.format(user.display_name)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='UN-MUTE: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                if reason:
                    log_embed.add_field(name='Reason', value=reason, inline=False)
                log_embed.add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

            await asyncio.sleep(10)
            await mute_message.delete()

            return

    @command('deafen', 0, description='Prevent a guild member from viewing or sending messages to a given text channel', usage='deafen [user] (channel) [reason]', permission='administrator text_deafen_members', private=False)
    async def text_deafen_command(self, author, channel, guild, content, user_mentions, channel_mentions, args):
        """Command that prevents a guild member from viewing or sending messages to a given text channel"""
        if not len(user_mentions) >= 1:
            return ChannelResponse(send_help=True)

        if not len(content) >= len(user_mentions[0].mention + ' '):
            reason = 'No Reason Provided'
        else:
            reason = content[len(user_mentions[0].mention + ' '):]

        user = user_mentions[0]

        if user == author:
            return ChannelResponse(content='*Muting one\'s self is rarely beneficial*')

        if self.permissions.has_any_permission(['administrator', 'text_deafen_members'], user, channel):
            return ChannelResponse(content='*Member can not be muted due to elevated mute permissions*')

        channel_perms = self.permissions.has_any_permission(['administrator', 'text_deafen_members'], author, channel)
        guild_perms = self.permissions.has_any_permission(['administrator', 'text_deafen_members'], author, channel.guild)

        target = None

        if len(channel_mentions) >= 1:
            if args[1] == channel_mentions[0].mention:
                target = channel_mentions[0]
                target_perms = self.permissions.has_any_permission(['administrator', 'text_deafen_members'], author, target)

                if not target.guild == guild:
                    return ChannelResponse(content='*Passed Channel must belong to the current Guild*')

                if not target_perms:
                    return ChannelResponse(content='**INVALID Permissions**: {} does not have the `administrator` or `text_deafen_members` permission in {}.'.format(author.display_name, target.mention))

                if not len(reason) >= len(target.mention + ' '):
                    reason = 'No Reason Provided'
                else:
                    reason = reason[len(target.mention + ' '):]

        if (not target) and (not guild_perms):
            target = channel

        log_channel = self.get_log_channel(guild)

        if target:
            if not target.permissions_for(user).read_messages:
                return ChannelResponse(content='*{} is already devoid of message viewing permissions in {}*'.format(user, target.mention))

            deafen_message = await channel.send(content=self.filter_mentions('Deafening {} in {}...'.format(user.display_name, target.mention)))

            try:
                await target.set_permissions(user, reason='TEXT-MUTE: {}'.format(reason), read_messages=False)
            except:
                await deafen_message.edit(content=self.filter_mentions('Error Deafening {} in {}.'.format(user.display_name, target.mention)))
                return

            await deafen_message.edit(content=self.filter_mentions('Deafened {} in {}.'.format(user.display_name, target.mention)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='DEAFEN: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                log_embed.add_field(name='Reason', value=reason, inline=False).add_field(name='Channel', value=target.mention, inline=False).add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

            await asyncio.sleep(10)
            await deafen_message.delete()

            return
        else:
            deafen_message = await channel.send(content=self.filter_mentions('Deafening {}...'.format(user.display_name)))

            error_channels = []

            static_channels = self.get_static_channels(guild)
            print(static_channels)
            print(channel.id)

            if channel.permissions_for(user).read_messages:
                if not channel.id in static_channels:
                    try:
                        await channel.set_permissions(user, reason='TEXT-DEAFEN: {}'.format(reason), read_messages=False)
                    except:
                        error_channels += [channel]

            for target in guild.text_channels:
                if target.permissions_for(user).read_messages and not channel == target:
                    if not target.id in static_channels:
                        try:
                            await target.set_permissions(user, reason='TEXT-DEAFEN: {}'.format(reason), read_messages=False)
                        except:
                            error_channels += [target]

            if error_channels:
                await deafen_message.edit(content=self.filter_mentions('Unable to deafen {} in {} of {} channels'.format(user, len(error_channels), len(guild.text_channels))))
            else:
                await deafen_message.edit(content=self.filter_mentions('Deafened {}...'.format(user.display_name)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='DEAFEN: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                log_embed.add_field(name='Reason', value=reason, inline=False).add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

            await asyncio.sleep(10)
            await deafen_message.delete()

            return

    @command('undeafen', 0, description='Return viewing and messaging permissions to a given guild member', usage='undeafen [user] (channel) [reason]', permission='administrator text_deafen_members', private=False)
    async def text_undeafen_command(self, author, channel, guild, content, user_mentions, channel_mentions, args):
        """Return viewing and messaging permissions to a given guild member"""
        if not len(user_mentions) >= 1:
            return ChannelResponse(send_help=True)

        if not len(content) >= len(user_mentions[0].mention + ' '):
            reason = None
        else:
            reason = content[len(user_mentions[0].mention + ' '):]

        user = user_mentions[0]

        channel_perms = self.permissions.has_any_permission(['administrator', 'text_deafen_members'], author, channel)
        guild_perms = self.permissions.has_any_permission(['administrator', 'text_deafen_members'], author, channel.guild)

        target = None

        if len(channel_mentions) >= 1:
            if args[1] == channel_mentions[0].mention:
                target = channel_mentions[0]
                target_perms = self.permissions.has_any_permission(['administrator', 'text_deafen_members'], author, target)

                if not target.guild == guild:
                    return ChannelResponse(content='*Passed Channel must belong to the current Guild*')

                if not target_perms:
                    return ChannelResponse(content='**INVALID Permissions**: {} does not have the `administrator` or `text_deafen_members` permission in {}.'.format(author.display_name, target.mention))

                if reason:
                    if not len(reason) >= len(target.mention + ' '):
                        reason = None
                    else:
                        reason = reason[len(target.mention + ' '):]

        if (not target) and (not guild_perms):
            target = channel

        log_channel = self.get_log_channel(guild)

        if target:
            if not target.permissions_for(user).read_messages == False:
                return ChannelResponse(content='*{} already has message viewing permissions in {}*'.format(user, target.mention))

            deafen_message = await channel.send(content=self.filter_mentions('Un-Deafening {} in {}...'.format(user.display_name, target.mention)))

            try:
                await target.set_permissions(user, reason='REMOVE TEXT-DEAFEN: {}'.format(reason), read_messages=None)
            except:
                await deafen_message.edit(content=self.filter_mentions('Error Un-Deafening {} in {}.'.format(user.display_name, target.mention)))
                return

            await deafen_message.edit(content=self.filter_mentions('Un-Deafened {} in {}.'.format(user.display_name, target.mention)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='UN-DEAFEN: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                if reason:
                    log_embed.add_field(name='Reason', value=reason, inline=False)
                log_embed.add_field(name='Channel', value=target.mention, inline=False).add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

                await asyncio.sleep(10)
                await deafen_message.delete()

            return
        else:
            deafen_message = await channel.send(content=self.filter_mentions('Un-Deafening {}...'.format(user.display_name)))

            error_channels = []

            if channel.permissions_for(user).read_messages == False:
                try:
                    await channel.set_permissions(user, reason='REMOVE TEXT-DEAFEN: {}'.format(reason), read_messages=None)
                except:
                    error_channels += [channel]

            for target in guild.text_channels:
                if target.permissions_for(user).read_messages == False and not channel == target:
                    try:
                        await target.set_permissions(user, reason='REMOVE TEXT-DEAFEN: {}'.format(reason), read_messages=None)
                    except:
                        error_channels += [target]

            if error_channels:
                await deafen_message.edit(content=self.filter_mentions('Unable to un-deafen {} in {} of {} channels'.format(user, len(error_channels), len(guild.text_channels))))
            else:
                await deafen_message.edit(content=self.filter_mentions('Un-Deafened {}...'.format(user.display_name)))

            if log_channel:
                log_embed = discord.Embed(color=discord.Colour.red()).set_author(name='UN-DEAFEN: {} ({}#{})'.format(user.display_name, user.name, user.discriminator), icon_url=user.avatar_url)
                if reason:
                    log_embed.add_field(name='Reason', value=reason, inline=False)
                log_embed.add_field(name='Responsible Moderator', value=author.display_name, inline=False)
                await log_channel.send(embed=log_embed)

            await asyncio.sleep(10)
            await deafen_message.delete()

            return
