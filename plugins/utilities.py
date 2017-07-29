"""UTILITIES PLUGIN"""

from plasmaBot.plugin import Plugin, ChannelResponse, command, event

from SQLiteHelper import SQLiteHelper as sq
from plasmaBot.utils import databaseTable

import discord

STATE_DEFAULTS = databaseTable(['USER_ID', 'STATE', 'MESSAGE'],
                               ['INT PRIMARY KEY NOT NULL', 'TEXT NOT NULL', 'TEXT NOT NULL'])

class Status(Plugin):
    """A Plugin full of useful commands and features"""

    NAME = 'Status'

    def on_plugin_load(self):
        """Event fired on plugin load.  Initializes Plugin elements."""
        self.db = sq.Connect('plasmaBot/data/status')

        if not self.db.table('user_state').tableExists():
            self.db.table('user_state').init(STATE_DEFAULTS)

    @command('afk', '0', description='Set your state as AFK!', usage='afk [afk_message]', permission='owner')
    async def afk_command(self, author, content, user_mentions, role_mentions):
        """Channel AFK command: Allows users to set their state as afk."""
        if author.bot:
            return ChannelResponse('Invalid! Bot Accounts are not allowed to be AFK!')

        afk_message = content.replace('\n', ' ').replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')

        for user in user_mentions:
            afk_message = afk_message.replace(user.mention, '@\u200b{}'.format(user.display_name))

        for role in role_mentions:
            afk_message = afk_message.replace(role.mention, '@\u200b{}'.format(role.name))

        if len(afk_message) > 200:
            return ChannelResponse('Invalid! AFK Message must be 200 characters or Less!')

        states = self.db.table('user_state').select('STATE').where('USER_ID').equals(author.id).execute()
        user_state = None

        for user in states:
            user_state = user[0]

        if user_state:
            self.db.table('user_state').update('STATE').setTo('AFK').where('USER_ID').equals(author.id).execute()
            self.db.table('user_state').update('MESSAGE').setTo(afk_message).where('USER_ID').equals(author.id).execute()
        else:
            self.db.table('user_state').insert(author.id, 'AFK', afk_message).into('USER_ID', 'STATE', 'MESSAGE')

        return ChannelResponse(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='{} is AFK:   {}'.format(author.display_name, afk_message), icon_url=author.avatar_url))

    @event
    async def on_message(self, message):
        pass
