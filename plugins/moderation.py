"""MODERATION PLUGIN"""

from plasmaBot.plugin import Plugin, ChannelResponse, command

from SQLiteHelper import SQLiteHelper as sq
from plasmaBot.utils import databaseTable

import discord

GUILD_DEFAULTS = databaseTable(['GUILD_ID', 'LOG_CHANNEL'],
                               ['INT PRIMARY KEY NOT NULL', 'INT NOT NULL'])


class Moderation(Plugin):
    """A Client Plugin that handles functionality vital to the moderation of servers"""

    NAME = 'Moderation'

    def on_plugin_load(self):
        """Event fired on plugin load.  Initializes Plugin elements."""
        self.db = sq.Connect('plasmaBot/data/status')

        if not self.db.table('guilds').tableExists():
            self.db.table('guilds').init(GUILD_DEFAULTS)

        self.permissions.register('manage_logs', False, 'Permissions')
        self.permissions.register('text_mute_members', False, 'Moderation')

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

            mute_message = await channel.send(content=self.filter_mentions('Muting {} in {}...'.format(user.display_name, target.mention)), delete_after=20)

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

            return
        else:
            mute_message = await channel.send(content=self.filter_mentions('Muting {}...'.format(user.display_name)), delete_after=20)

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

            mute_message = await channel.send(content=self.filter_mentions('Un-Muting {} in {}...'.format(user.display_name, target.mention)), delete_after=20)

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

            return
        else:
            mute_message = await channel.send(content=self.filter_mentions('Un-Muting {}...'.format(user.display_name)), delete_after=20)

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

            return
