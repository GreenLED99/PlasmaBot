from plasmaBot.plugin import PBPlugin, PBPluginMeta, Response
import discord

from plasmaBot import exceptions
import discord

from SQLiteHelper import SQLiteHelper as sq

import logging
log = logging.getLogger('discord')

class ServerSecurity(PBPlugin):
    name = 'Server Security'
    requirements = None
    is_global = True

    def __init__(self, plasmaBot):
        super().__init__(plasmaBot)

        self.db = sq.Connect(self.bot.config.security_db)

    async def cmd_getroles(self, message):
        """
        You screwed up
        """
        roles = message.server.roles
        ret = ""
        for role in roles:
            ret = ret + role.name + ": " + role.id + "\r"
        ret = ret.replace("@" , "**@**")
        return Response(ret, reply=False, delete_after=60)

    async def cmd_setupsecurity(self, message, roleID, channelID):
        """
        Usage:
            {command_prefix}setupsecurity (role ID) (channel ID)

        Ill tell you what this is once I figure out what this is
        """
        server = message.server
        verified_role = discord.utils.get(server.roles, id=roleID)
        everyone_role = discord.utils.get(server.roles, name="@everyone")

        #Change to if everyone can see, let verified see
        overwrite = discord.PermissionOverwrite(read_messages = True)
        for channel in server.channels:
            await self.bot.edit_channel_permissions(channel, verified_role, overwrite)

        overwrite = discord.PermissionOverwrite(read_messages = False)
        for channel in server.channels:
            await self.bot.edit_channel_permissions(channel, everyone_role, overwrite)



        for member in server.members:
            if verified_role not in member.roles:
                await self.bot.add_roles(member, verified_role)




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
