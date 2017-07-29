"""PLASMABOT ERROR AND MESSAGE LOGGER"""

import discord

class Logger(object):
    """Class that handles error and message logging"""
    def __init__(self, client):
        self.client = client
        self.config = client.config
        self.permissions = client.permissions
        self.printer = client.printer

        self.initialized = False
        self.traceback_channel = None

    async def initialize_log_channels(self):
        """Method that handles registration of log channels"""
        if self.config['logging']['errors']['enabled']:
            self.traceback_channel = self.client.get_channel(self.config['logging']['errors']['channel'])
            if not self.traceback_channel:
                self.printer.indicate('[LOGGER] No Traceback Channel Found.')
        else:
            self.traceback_channel = None

        self.initialized = True

    async def error(self, user, location, context, traceback):
        """Log an error to the traceback channel"""
        if location == self.traceback_channel:
            return

        if self.traceback_channel == None:
            return

        error_embed = discord.Embed(title='Error Traceback', color=discord.Colour.red())
        error_embed.add_field(name='User', value=user.display_name, inline=False)

        if isinstance(location, discord.abc.PrivateChannel):
            error_embed.add_field(name='Location', value='Direct Message', inline=False)
        elif isinstance(location, discord.abc.GuildChannel):
            error_embed.add_field(name='Location', value='{} in {}'.format(location.mention if isinstance(location, discord.TextChannel) else '{} (VC)'.format(location.name), location.guild.name), inline=False)
        elif isinstance(location, discord.Guild):
            error_embed.add_field(name='Location', value=location.name, inline=False)

        error_embed.add_field(name='Context', value='`{}`'.format(context), inline=False).add_field(name='Traceback', value='```{}```'.format(traceback), inline=False)
        error_embed.set_footer(text='{} Traceback Log'.format(self.config['presence']['name']), icon_url=self.client.user.avatar_url)

        await self.traceback_channel.send(embed=error_embed)

        return
