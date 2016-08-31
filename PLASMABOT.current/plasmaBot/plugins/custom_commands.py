from plasmaBot.plugin import PBPlugin, PBPluginMeta, Response
import discord

from plasmaBot import exceptions

from SQLiteHelper import SQLiteHelper as sq

import logging
log = logging.getLogger('discord')

class CustomCommands(PBPlugin):
    name = 'Custom Commands'
    globality = 'all'
    help_exclude = False

    def __init__(self, plasmaBot):
        super().__init__(plasmaBot)
        self.db = sq.Connect('data/custom')

    def create_table(self, server_id):
        if not self.db.table(self.get_table_name(server_id)).tableExists():
            self.db.table(self.get_table_name(server_id)).withColumns("COMMAND", "RESPONSE").withDataTypes("TEXT PRIMARY KEY NOT NULL", "TEXT").createTable()

    def get_table_name(self, server_id):
        return "S" + server_id

    async def cmd_custom(self, server, leftover_args):
        """
        Usage:
            {command_prefix}command_key (required arguments have parenthesis) [optional_arguments have brackets]

        A string about how the plugin works
        """

        self.create_table(server.id)
        try:
            name = leftover_args[0]
            del leftover_args[0]
        except:
            return Response("Must include name of command as argument.", reply=False, delete_after=45)

        test_return = self.db.table(self.get_table_name(server.id)).select("RESPONSE").where("COMMAND").equals(name).execute()
        try:
            return Response(test_return.fetchall()[0][0], reply=False, delete_after=45)
        except:
            return Response("Command does not exist.", reply=False, delete_after=45)

    async def cmd_customlist(self, server):
        """
        Usage:
            {command_prefix}command_key (required arguments have parenthesis) [optional_arguments have brackets]

        A string about how the plugin works
        """

        self.create_table(server.id)
        test_return = self.db.table(self.get_table_name(server.id)).select("COMMAND").execute()
        ret = "List of all custom commands:\n"
        for cmd in test_return:
            ret = ret + cmd[0] + "\n"
        return Response(ret, reply=False, delete_after=45)

    async def cmd_customcreate(self, server, leftover_args):
        """
        Usage:
            {command_prefix}command_key (required arguments have parenthesis) [optional_arguments have brackets]

        A string about how the plugin works
        """

        if len(leftover_args) == 1:
            return Response("Response cannot be null.", reply=False, delete_after=45)

        self.create_table(server.id)
        try:
            name = leftover_args[0]
            del leftover_args[0]
        except:
            return Response("Must include name of command as first argument. Following message will be command's return statement.", reply=False, delete_after=45)

        try:
            response = ''
            for partial_msg in leftover_args:
                response += partial_msg + ' '
            response = response[:-1]
        except:
            return Response("Problem with second arg. Fight me.", reply=False, delete_after=45)

        test_return = self.db.table(self.get_table_name(server.id)).select("RESPONSE").where("COMMAND").equals(name).execute()

        if len(test_return.fetchall()) >= 1:
            return Response("Custom command " + name + " already exists. Please delete that entry before making a new one.", reply=False, delete_after=45)
        else:
            self.db.table(self.get_table_name(server.id)).insert(name, response).into("COMMAND", "RESPONSE")
            return Response("Command '" + name + "' created with response ```" + response + "```", reply=False, delete_after=45)


    async def cmd_customdelete(self, server, leftover_args):
        """
        Usage:
            {command_prefix}command_key (required arguments have parenthesis) [optional_arguments have brackets]

        A string about how the plugin works
        """

        self.create_table(server.id)

        try:
            test_return = self.db.table(self.get_table_name(server.id)).select("RESPONSE").where("COMMAND").equals(leftover_args[0]).execute()
        except:
            return Response("Must include command name to delete", reply=False, delete_after=45)

        if len(test_return.fetchall()) >= 1:
            self.db.table(self.get_table_name(server.id)).delete().where("COMMAND").equals(leftover_args[0]).execute()
            return Response("Custom command " + leftover_args[0] + " deleted.", reply=False, delete_after=45)
        else:
            return Response("Command '" + leftover_args[0] + "' does not exist.", reply=False, delete_after=45)





#this comment is to stop save whitespace deletion
