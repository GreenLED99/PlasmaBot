from plasmaBot.plugin import PBPlugin, PBPluginMeta, Response, PBPluginConfig
import discord

from plasmaBot import exceptions

from SQLiteHelper import SQLiteHelper as sq

import logging
log = logging.getLogger('discord')

class PredictionsChat(PBPlugin):
    name = 'Predictions Chat'
    globality = 'all'
    help_exclude = False

    def __init__(self, plasmaBot):
        super().__init__(plasmaBot)

        self.pl_config = PBPluginConfig(plasmaBot, 'predictions.ini', 'PREDICTIONS CHAT', {'Files':[['predictions_db_location', 'The location of the prediction database', 'data/predictions']], 'Channel':[['server_id', 'The ID of the server', '226572892471558144'],['channel_id', 'The ID of the channel', '228384812136661003']]})

        self.db = sq.Connect(self.pl_config.predictions_db_location)

        if not self.db.table("Predictions").tableExists():
            self.db.table("Predictions").withColumns("ID").withDataTypes("TEXT PRIMARY KEY NOT NULL").createTable()

        self.server = self.pl_config.server_id
        self.channel = self.pl_config.channel_id
        self.bot_deleted_messages = []

    async def on_message(self, message, message_type, message_context):
        if (not message.author.bot) and message.server.id == self.server and message.channel.id == self.channel:
            people = self.db.table('Predictions').select("ID").where("ID").equals(message.author.id).execute()

            userID = None
            for person in people:
                userID = person[0]

            if userID == None:
                #Person has not posted yet
                await self.bot.safe_send_message(message.channel, message.author.mention + " has just posted their prediction!", tts=False, expire_in=60)
                self.db.table("Predictions").insert(message.author.id).into("ID")
            else:
                #Person has already posted
                await self.bot.safe_send_message(message.channel, message.author.mention + ", you have already posted a prediction. Please add your message as an edit to your previous prediction:```" + message.content + "```", tts=False, expire_in=60)
                self.bot_deleted_messages.append(message.id)
                await self.bot.delete_message(message)


    async def on_message_edit(self, message, new_message):
        if (not message.author.bot) and message.server.id == self.server and message.channel.id == self.channel:
            await self.bot.safe_send_message(message.channel, message.author.mention + " has just edited their prediction!", tts=False, expire_in=60)

    async def on_message_delete(self, message):
        if (message.id not in self.bot_deleted_messages) and (not message.author.bot) and message.channel.id == self.channel:
            await self.bot.safe_send_message(message.channel, message.author.mention + "'s prediction has been deleted.", tts=False, expire_in=60)
            self.db.table("Predictions").delete().where("ID").equals(message.author.id).execute()
        else:
            if message.id in self.bot_deleted_messages:
                self.bot_deleted_messages.remove(message.id)
