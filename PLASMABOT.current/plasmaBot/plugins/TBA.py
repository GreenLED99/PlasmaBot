from plasmaBot.plugin import PBPlugin, PBPluginMeta, Response
import discord

from plasmaBot import exceptions
import discord

from plasmaBot.resources.TBAPythonAPI import *

import logging
log = logging.getLogger('discord')

class TBAPlugin(PBPlugin):
    name = 'TBA (The Blue Alliance) Plugin'
    requirements = None
    is_global = True


    def __init__(self, plasmaBot):
        super().__init__(plasmaBot)
        self.TBA = TBAParser(2403, "Discord Bot", "0.1.0")

    async def cmd_test_tba(self, message):
        """
        You screwed up
        """
        test = self.TBA.get_team('frc2403')
        what = test.nickname
        return Response(what, reply=True, delete_after=20)

    async def cmd_setupsecurity(self, message, roleID, channelID):
        """
        Usage:
            {command_prefix}setupsecurity (role ID) (channel ID)

        Ill tell you what this is once I figure out what this is
        """
