"""RANK PLUGIN"""
from plasmaBot.plugin import Plugin, ChannelResponse, TerminalResponse, command, event

from SQLiteHelper import SQLiteHelper as sq
from plasmaBot.utils import databaseTable

import discord
import random

RANK_LOG = databaseTable(['USER_ID','xp', 'rank'],
                                ['INT PRIMARY KEY NOT NULL', 'INT PRIMARY KEY NOT NULL', 'TEXT NOT NULL'])

class Rank(Plugin):
	"""A Plugin used to track activity on the server"""
	
	NAME = 'rank'
	
	def on_plugin_load(self):
        """Event fired on plugin load.  Initializes Plugin elements."""
        self.db = sq.Connect('plasmaBot/data/rank')

        if not self.db.table('rank').tableExists():
            self.db.table('rank').init(RANK_LOG)
	
	@event
	async def on_message(self, message):
		"""PLUGIN EVENT: Client.on_message()"""
		prefix = self.config['presence']['prefix']
		if not message.content == '':
			if author.id != db.table
			xp_add = db.table("rank").where("USER_ID").equals(author.id).execute()
			xp_add + random.randint(1,101)
			db.table("rank").update("xp").setTo("xp_add").where("USER_ID").equals(author.id).execute()
