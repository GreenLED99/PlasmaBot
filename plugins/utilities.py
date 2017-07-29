"""UTILITIES PLUGIN"""

from plasmaBot.plugin import Plugin, ChannelResponse, command, event

from SQLiteHelper import SQLiteHelper as sq
from plasmaBot.utils import databaseTable

import discord

STATUS_DEFAULTS = databaseTable(['USER_ID', 'STATUS', 'MESSAGE'],
                               ['INT PRIMARY KEY NOT NULL', 'TEXT NOT NULL', 'TEXT NOT NULL'])

class Status(Plugin):
    """A Plugin full of useful commands and features"""

    NAME = 'Status'

    def on_plugin_load(self):
        """Event fired on plugin load.  Initializes Plugin elements."""
        self.db = sq.Connect('plasmaBot/data/status')

        if not self.db.table('status').tableExists():
            self.db.table('status').init(STATUS_DEFAULTS)

    @command('afk', '0', description='Set your state as AFK!', usage='afk [afk_message]')
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

        states = self.db.table('status').select('STATUS').where('USER_ID').equals(author.id).execute()
        user_status = None

        for user in states:
            user_status = user[0]

        if user_status:
            self.db.table('status').update('STATUS').setTo('AFK').where('USER_ID').equals(author.id).execute()
            self.db.table('status').update('MESSAGE').setTo(afk_message).where('USER_ID').equals(author.id).execute()
        else:
            self.db.table('status').insert(author.id, 'AFK', afk_message).into('USER_ID', 'STATUS', 'MESSAGE')

        return ChannelResponse(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='{} is AFK:   {}'.format(author.display_name, afk_message), icon_url=author.avatar_url), expire=None)

    @command('sleep', '0', description='Set your state as asleep!', usage='sleep')
    async def sleep_command(self, author):
        """Channel AFK command: Allows users to set their state as asleep."""
        if author.bot:
            return ChannelResponse('Invalid! Bot Accounts are not allowed to be asleep!')

        states = self.db.table('status').select('STATUS').where('USER_ID').equals(author.id).execute()
        user_status = None

        for user in states:
            user_status = user[0]

        if user_status:
            self.db.table('status').update('STATUS').setTo('asleep').where('USER_ID').equals(author.id).execute()
            self.db.table('status').update('MESSAGE').setTo('').where('USER_ID').equals(author.id).execute()
        else:
            self.db.table('status').insert(author.id, 'asleep', '').into('USER_ID', 'STATUS', 'MESSAGE')

        return ChannelResponse(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='{} is now sleeping... 💤'.format(author.display_name), icon_url=author.avatar_url), expire=None)

    async def clear_status(self, user, channel):
        """Clear the status of a given user from the status database table"""
        states = self.db.table('status').select('STATUS').where('USER_ID').equals(user.id).execute()
        user_status = None

        for entry in states:
            user_status = entry[0]

        if user_status:
            async with channel.typing():
                self.db.table('status').delete().where('USER_ID').equals(user.id).execute()
                await channel.send(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='{} is no longer {}.'.format(user.display_name, user_status), icon_url=user.avatar_url), delete_after=15)

    async def announce_status(self, mentions, channel):
        """Announce the AFK status of a given user in a given channel"""
        if len(mentions) == 0:
            return

        offline_members = []

        afk_members = []
        sleep_members = []

        for user in mentions:
            states = self.db.table('status').select('STATUS', 'MESSAGE').where('USER_ID').equals(user.id).execute()
            user_status = None
            message = ''

            for entry in states:
                user_status = entry[0]
                message = entry[1]

            offline_members += [user]

            if user_status == 'AFK':
                afk_members += [[user, message]]
            elif user_status == 'asleep':
                sleep_members += [user]

        if len(offline_members) == 1:
            if len(afk_members) == 1:
                async with channel.typing():
                    await channel.send(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='{} is AFK: {}'.format(afk_members[0][0].display_name, afk_members[0][1]), icon_url=afk_members[0][0].avatar_url), delete_after=15)
            elif len(sleep_members) == 1:
                async with channel.typing():
                    await channel.send(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='{} is sleeping.  💤'.format(afk_members[0][0].display_name), icon_url=afk_members[0][0].avatar_url), delete_after=15)
        elif len(offline_members) >= 1:
            async with channel.typing():
                if len(offline_members) >= 10:
                    await channel.send(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='Many people are Offline', icon_url=self.client.user.avatar_url), delete_after=15)
                else:
                    users = '{}'.format(offline_members.pop(0)[0].display_name)
                    end_users = ' & {}'.format(offline_members.pop(-1)[0].display_name)

                    for user in offline_members:
                        users += ', {}'.format(user[0].display_name)

                    await channel.send(embed=discord.Embed(color=discord.Colour.purple()).set_author(name='{} are Offline'.format(users + end_users), icon_url=self.client.user.avatar_url), delete_after=15)


    @event
    async def on_message(self, message):
        """PLUGIN EVENT: Client.on_message()"""
        if not message.content.lower().startswith('{}afk'.format(self.config['presence']['prefix'])) and not message.content.startswith('{}sleep'.format(self.config['presence']['prefix'])):
            await self.clear_status(message.author, message.channel)
            await self.announce_status(message.mentions, message.channel)
