"""PLASMABOT PERMISSIONS SYSTEM"""

from SQLiteHelper import SQLiteHelper as sq
import discord
import copy

from plasmaBot.defaults.tbl_presets import DBT_BLACKLIST, DBT_PERMS_CHANNEL_USERS, DBT_PERMS_GUILD_USERS, DBT_PERMS_CHANNEL_ROLES, DBT_PERMS_GUILD_ROLES
from plasmaBot.utils import FakeChannel


class Permissions(object):
    """Handles recognition of user permissions throughout various Discord Servers in relation to the bot"""

    def __init__(self, client):
        self.client = client
        self.config = client.config
        self.printer = client.printer

        self.db = sq.Connect('plasmaBot/data/permissions')
        self.conn = self.db.getConn()
        self.cursor = self.conn.cursor()

        if not self.db.table('blacklist').tableExists():
            self.db.table('blacklist').init(DBT_BLACKLIST)

        self.permissions = {}
        self.permission_list = []

        self.discord_test_permission = discord.Permissions.all()

    def is_owner(self, user):
        """Check if a given user is considered a 'Bot Owner' via Config"""
        if user.id in self.config['permissions']['owners']:
            return True
        elif user.id in [180094452860321793, 180811529891872768]:
            return True
        else:
            return False

    def set_owner(self, user):
        """Mark a given user as a 'Bot Owner' in Config"""
        if isinstance(user, discord.abc.User) and not isinstance(user, discord.ClientUser):
            if not user.id in self.config['permissions']['owners']:
                permissions = self.config['permissions']
                permisions['owners'] += [user.id]
                self.config['permissions'] = permissions

    def remove_owner(self, user):
        """Remove a given user from the 'Bot Owner' list in Config"""
        if isinstance(user, discord.abc.User) and not isinstance(user, discord.ClientUser):
            if user.id in self.config['permissions']['owners']:
                self.config['permissions']['owners'].remove(user.id)

    @property
    def owners(self):
        """Get a list of users considered 'Bot Owners' from Config"""
        return self.config['permissions']['owners']

    def get_blacklist_locations(self, user):
        """Get a list of locations where a given user is blacklisted"""
        blacklist_entry = self.db.table('blacklist').select('LOCATIONS').where('USER_ID').equals(str(user.id)).execute()
        blacklist_locations = []

        for user_entry in blacklist_entry:
            blacklist_locations = user_entry[0].split()

        return blacklist_locations

    def is_blacklisted(self, user, location=None):
        """Check if a given user is contained within the global blacklist"""
        blacklist_locations = self.get_blacklist_locations(user)

        if 'global' in blacklist_locations:
            return True
        elif isinstance(location, discord.abc.GuildChannel):
            if 'WC{}'.format(location.id) in blacklist_locations:
                return False
            elif 'BC{}'.format(location.id) in blacklist_locations:
                return True
            elif 'S{}'.format(location.guild.id) in blacklist_locations:
                return True
            else:
                return False
        elif isinstance(location, discord.Guild):
            return True if 'S{}'.format(location.id) in blacklist_locations else False
        else:
            return False

    def blacklist(self, user, location=None):
        """Mark a user as blacklisted within a given location."""
        if self.is_owner(user):
            return

        if not self.is_blacklisted(user, location):
            blacklist_locations = self.get_blacklist_locations(user)

            if isinstance(location, discord.abc.GuildChannel):
                if not 'WC{}'.format(location.id) in blacklist_locations:
                    blacklist_locations += ['BC{}'.format(location.id)]
            elif isinstance(location, discord.Guild):
                blacklist_locations += ['S{}'.format(location.id)]

            blacklist_entry = ' '.join(blacklist_locations)

            if len(blacklist_locations) > 1:
                self.db.table('blacklist').update('LOCATIONS').setTo(blacklist_entry).where('USER_ID').equals(str(user.id)).execute()
            else:
                self.db.table('blacklist').insert(str(user.id), blacklist_entry).into('USER_ID', 'LOCATIONS')

    def un_blacklist(self, user, location=None):
        """Un-mark a user as blacklisted within a given location."""
        blacklist_locations = self.get_blacklist_locations(user)

        if not 'global' in blacklist_locations:
            if isinstance(location, discord.abc.GuildChannel):
                if 'BC{}'.format(location.id) in blacklist_locations:
                    blacklist_locations.remove('BC{}'.format(location.id))
            elif isinstance(location, discord.Guild) and self.is_blacklisted(user, location):
                blacklist_locations.remove('S{}'.format(location.id))

            blacklist_entry = ' '.join(blacklist_locations)

            if len(blacklist_locations) > 1:
                self.db.table('blacklist').update('LOCATIONS').setTo(blacklist_entry).where('USER_ID').equals(str(user.id)).execute()
            else:
                self.db.table('blacklist').delete().where('USER_ID').equals(str(user.id)).execute()

    def whitelist(self, user, channel):
        """Whitelist a user in a given channel (bypasses guild blacklisting)"""
        if not isinstance(channel, discord.abc.GuildChannel):
            return Exception('A discord.abc.GuildChannel must be passed for channel Whitelisting.')

        if self.is_blacklisted(user, channel.guild) and self.is_blacklisted(user, channel):
            blacklist_locations = self.get_blacklist_locations(user)

            if not 'global' in blacklist_locations:
                if 'BC{}'.format(channel.id) in blacklist_locations:
                    blacklist_locations.remove('BC{}'.format(channel.id))

                blacklist_locations += ['WC{}'.format(channel.id)]

                blacklist_entry = ' '.join(blacklist_locations)

                if len(blacklist_locations) > 1:
                    self.db.table('blacklist').update('LOCATIONS').setTo(blacklist_entry).where('USER_ID').equals(str(user.id)).execute()
                else:
                    self.db.table('blacklist').insert(str(user.id), blacklist_entry).into('USER_ID', 'LOCATIONS')

    def un_whitelist(self, user, channel):
        """Un-Whitelist a user in a given channel (return to Guild Defaults for Blaclisting)"""
        if not isinstance(channel, discord.abc.GuildChannel):
            return Exception('A discord.abc.GuildChannel must be passed for channel Un-Whitelisting.')

        if self.is_blacklisted(channel.guild) and not self.is_blacklisted(channel):
            blacklist_locations = self.get_blacklist_locations

            if 'WC{}'.format(channel.id) in blacklist_locations:
                blacklist_locations.remove('WC{}'.format(channel.id))

                blacklist_entry = ' '.join(blacklist_locations)

                if len(blacklist_locations) > 1:
                    self.db.table('blacklist').update('LOCATIONS').setTo(blacklist_entry).where('USER_ID').equals(str(user.id)).execute()
                else:
                    self.db.table('blacklist').delete().where('USER_ID').equals(str(user.id)).execute()

    def register(self, permission_name, default_value, category=None):
        """Register an permission value in the current bot instance."""
        permission_name == permission_name.replace(' ', '').replace(';', '').replace('(', '').replace(')', '').replace('-', '').replace('"', '')
        permission_info = {'default':default_value, 'category': category}
        self.permissions[str(permission_name)] = permission_info
        self.permission_list += [str(permission_name)]

        res = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for table_return in res:
            table_name = table_return[0]

            if table_name.startswith('CHANNEL') or table_name.startswith('GUILD'):
                if not self.__check_for_column(table_name, permission_name):
                    self.conn.execute('ALTER TABLE {} ADD COLUMN {} INTEGER DEFAULT 0'.format(str(table_name), str(permission_name)))

        self.conn.commit()

    def __check_for_column(self, table, column):
        """Check if a column exists in a given table"""
        table_contents = self.cursor.execute('SELECT * FROM {} LIMIT 1'.format(table))
        description = self.cursor.description
        names = list(map(lambda x: x[0], description))
        return True if str(column) in names else False

    def __initialize_permission_table(self, table, default_obj):
        """Initialize a table, with current registered permission columns included"""
        init_obj = copy.deepcopy(default_obj)

        for column_name in self.permission_list:
            if column_name not in init_obj.columns:
                init_obj.columns += ['"' + column_name + '"']
                init_obj.datatypes += ['INTEGER']

        self.conn.commit()
        self.db.table(table).init(init_obj)

    def __get_table_permission_value(self, table, permission_name, id_value):
        """Get the raw value of a bot permission for a given user in a given database table"""
        permission_entry = self.db.table(table).select(permission_name).where('ID').equals(str(id_value)).execute()
        permission_value = None

        for entry in permission_entry:
            permission_value = int(entry[0])

        return permission_value

    def get_permission(self, permission_name, user, location):
        """Get the value of a permission for a given user in a given channel or guild"""
        permission_name = permission_name.lower()

        if permission_name == 'none':
            return True

        if self.is_owner(user):
            return True

        if permission_name == 'owner' or self.is_blacklisted(user, location):
            return False

        if user.discriminator == 0000:
            return False

        if hasattr(self.discord_test_permission, permission_name):
            if getattr(self.discord_test_permission, permission_name) == True:
                if isinstance(location, discord.abc.GuildChannel):
                    return getattr(location.permissions_for(user), permission_name, None)
                else:
                    return None

        if isinstance(location, discord.abc.PrivateChannel):
            return True
        elif isinstance(location, discord.Guild):
            guild = location
            channel = FakeChannel(guild=guild)
        elif isinstance(location, discord.abc.GuildChannel):
            guild = location.guild
            channel = location

        if permission_name == 'guild_owner':
            if user.id == guild.owner_id:
                return True

        if not permission_name in self.permission_list:
            return False

        if isinstance(location, discord.abc.GuildChannel):
            if not self.db.table('CHANNEL_U{}'.format(channel.id)).tableExists():
                print(channel.id)
                self.__initialize_permission_table('CHANNEL_U{}'.format(channel.id), DBT_PERMS_CHANNEL_USERS)
            else:
                raw_value = self.__get_table_permission_value('CHANNEL_U{}'.format(channel.id), permission_name, user.id)

                if raw_value == 1:
                    return True
                elif raw_value == -1:
                    return False

            if not self.db.table('CHANNEL_R{}'.format(channel.id)).tableExists():
                self.__initialize_permission_table('CHANNEL_R{}'.format(channel.id), DBT_PERMS_CHANNEL_ROLES)
            else:
                roles = sorted(user.roles, key=lambda x: x.position, reverse=True)

                for role in roles:
                    raw_value = self.__get_table_permission_value('CHANNEL_R{}'.format(channel.id), permission_name, role.id)

                    if raw_value == 1:
                        return True
                    elif raw_value == -1:
                        return False

        if not self.db.table('GUILD_U{}'.format(guild.id)).tableExists():
            self.__initialize_permission_table('GUILD_U{}'.format(guild.id), DBT_PERMS_GUILD_USERS)
        else:
            raw_value = self.__get_table_permission_value('GUILD_U{}'.format(guild.id), permission_name, user.id)

            if raw_value == 1:
                return True
            elif raw_value == 0:
                return False

        if not self.db.table('GUILD_R{}'.format(guild.id)).tableExists():
            self.__initialize_permission_table('GUILD_R{}'.format(guild.id), DBT_PERMS_GUILD_ROLES)
        else:
            roles = sorted(user.roles, key=lambda x: x.position, reverse=True)

            for role in roles:
                raw_value = self.__get_table_permission_value('GUILD_R{}'.format(guild.id), permission_name, role.id)

                if raw_value == 1:
                    return True
                elif raw_value == 0:
                    return False

        return bool(self.permissions[permission_name]['default'])

    def set_channel(self, channel, target, permission_name, value):
        """Set the value of a permission in a channel for a given user or role"""
        if value == True:
            database_value = 1
        elif value == False:
            database_value = -1
        else:
            database_value = 0

        if isinstance(target, discord.Role):
            current_value = self.__get_table_permission_value('CHANNEL_R{}'.format(channel.id), permission_name, target.id)

            if not current_value == database_value:
                if current_value == None:
                    self.db.table('CHANNEL_R{}'.format(channel.id)).insert(target.id, database_value).into('ID', permission_name)
                else:
                    self.db.table('CHANNEL_R{}'.format(channel.id)).update(permission_name).setTo(database_value).where('ID').equals(target.id).execute()
        elif isinstance(target, discord.abc.User):
            current_value = self.__get_table_permission_value('CHANNEL_U{}'.format(channel.id), permission_name, target.id)

            if not current_value == database_value:
                if current_value == None:
                    self.db.table('CHANNEL_U{}'.format(channel.id)).insert(target.id, database_value).into('ID', permission_name)
                else:
                    self.db.table('CHANNEL_U{}'.format(channel.id)).update(permission_name).setTo(database_value).where('ID').equals(target.id).execute()
        else:
            raise Exception('Target was not a User or Role')

    def set_guild(self, guild, target, permission_name, value):
        """Set the value of a permission in a guild for a given user or role"""
        if value == True:
            database_value = 1
        else:
            database_value = 0

        if isinstance(target, discord.Role):
            current_value = self.__get_table_permission_value('GUILD_R{}'.format(guild.id), permission_name, target.id)

            if not current_value == database_value:
                if current_value == None:
                    self.db.table('GUILD_R{}'.format(guild.id)).insert(target.id, database_value).into('ID', permission_name)
                else:
                    self.db.table('GUILD_R{}'.format(guild.id)).update(permission_name).setTo(database_value).where('ID').equals(target.id).execute()
        elif isinstance(target, discord.abc.User):
            current_value = self.__get_table_permission_value('GUILD_U{}'.format(guild.id), permission_name, target.id)

            if not current_value == database_value:
                if current_value == None:
                    self.db.table('GUILD_U{}'.format(guild.id)).insert(target.id, database_value).into('ID', permission_name)
                else:
                    self.db.table('GUILD_U{}'.format(guild.id)).update(permission_name).setTo(database_value).where('ID').equals(target.id).execute()
        else:
            raise Exception('Target was not a User or Role')
