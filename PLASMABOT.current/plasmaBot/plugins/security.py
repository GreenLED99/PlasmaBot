from plasmaBot.plugin import PBPlugin, PBPluginMeta, Response
import discord

from plasmaBot import exceptions

from SQLiteHelper import SQLiteHelper as sq

import logging
log = logging.getLogger('discord')

class ServerSecurity(PBPlugin):
    name = 'Moderation Tools'
    requirements = None
    is_global = True

    def __init__(self, plasmaBot):
        super().__init__(plasmaBot)

        self.db = sq.Connect(self.bot.config.security_db)

    async def cmd_whateveruwanttomakeit(self, message, message_type, message_context, argument1, argument2):
        """
        Usage:
            {command_prefix}command (arguments) (like) (this)

        A Statement about what this is useful for that will show if no arguments listed.
        """

    # What I think this should do:
    # have a setup command that passes a role ID to be used for the verified ID and a channelID to be used as the entrance ID
    #  - command logs server ID, channel ID, and verified ID in a database
    #  - sets channel (by the ID given) to be visible by the @everyone role but disables it on all other roles on the server
    #  - sets all channels visible by @everyone to be invisible to the @everyone role, but visible to the verified role
    # on member join, ask a question from a SQL table for that server (aka, there is a global table for server tracking and a table for each server that store's that server's questions)
    #  - if correct, give them verified role
    #  - if false, tell them they can try again in 5 minutes
    #  - after 5 minutes, send them a direct message where they can try being verified again
    # A command to add questions to the server list
    # A command to list questions, along with a numeral ID that corresponds to the questions
    # A command to remove a question, by the numeral ID
    # a command to edit a question and answer, by the numeral ID

    # for now, just make all commands able to be used by everyone.  After I finish the plugin I'm working on, I'll start work on a permissions system we can add later to these plugins.

    # any questions, send me a DM and I'll try to hop on voice if it's not too late.
