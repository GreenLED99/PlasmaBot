"""RANK PLUGIN"""
from plasmaBot.plugin import Plugin, ChannelResponse, TerminalResponse, command, event

from SQLiteHelper import SQLiteHelper as sq
from plasmaBot.utils import databaseTable

import discord
import random

RANK_LOG = databaseTable(['USER_ID','xp', 'level', 'rank', 'cooldown'], ['INT PRIMARY KEY NOT NULL', 'INT', 'INT','STRING','INT'])

class Rank(Plugin):
    """A Plugin used to track activity on the server"""

    NAME = 'rank'
    help_exlcude = True

    def on_plugin_load(self):
        """Event fired on plugin load.  Initializes Plugin elements."""
        self.db = sq.Connect('plasmaBot/data/rank')

        if not self.db.table('rank').tableExists():
            self.db.table('rank').init(RANK_LOG)

    @event
    async def on_message(self, message):
        """PLUGIN EVENT: Client.on_message()"""
        prefix = self.config['presence']['prefix']
        """
        TO DO:
                ~Add users to database
                    -Check if user is in db before XP added
                ~learn timer function for cooldown
                    -skip XP add when timer is not at 0 and reset when XP added
                ~add customizable values for XP that can be set in config 
                    -(LOW PRIORITY)
        """
                
        if not message.content == '':
            xp_add = db.table("rank").where("USER_ID").equals(author.id).execute()
            xp_add + random.randint(1,101) #values customizable to whatever is wanted
            db.table("rank").update("xp").setTo("xp_add").where("USER_ID").equals(author.id).execute() #update the database with new XP
