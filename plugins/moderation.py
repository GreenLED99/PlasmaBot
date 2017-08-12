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
