"""Database Table Presets"""

from plasmaBot.utils import databaseTable

DBT_COMMANDS = databaseTable(['HANDLER', 'PLUGIN', 'METHOD_NAME', 'TYPE', 'DESCRIPTION', 'USAGE', 'HIDDEN', 'PRIVATE', 'PERMISSION'],
                             ['TEXT NOT NULL', 'TEXT NOT NULL', 'TEXT NOT NULL', 'INTEGER NOT NULL', 'TEXT DEFAULT "NONE"', 'TEXT DEFAULT "NONE"', 'INTEGER NOT NULL', 'INTEGER NOT NULL', 'TEXT NOT NULL'])

DBT_PLUGINS = databaseTable(['CLASS_NAME', 'FANCY_NAME', 'ENABLED', 'G_WHITELIST', 'C_WHITELIST', 'G_BLACKLIST', 'C_BLACKLIST'],
                            ['TEXT PRIMARY KEY NOT NULL', 'TEXT DEFAULT ""', 'INTEGER NOT NULL', 'TEXT DEFAULT ""', 'TEXT DEFAULT ""', 'TEXT DEFAULT ""', 'TEXT DEFAULT ""'])

DBT_EVENTS = databaseTable(['EVENT_NAME', 'PLUGIN'],
                           ['TEXT NOT NULL', 'TEXT NOT NULL'])

DBT_BLACKLIST = databaseTable(['USER_ID', 'LOCATIONS'],
                              ['TEXT PRIMARY KEY NOT NULL', 'TEXT NOT NULL'])

DBT_PERMS_CHANNEL_USERS = databaseTable(['ID'], ['TEXT PRIMARY KEY NOT NULL'])

DBT_PERMS_GUILD_USERS = databaseTable(['ID'], ['TEXT PRIMARY KEY NOT NULL'])

DBT_PERMS_CHANNEL_ROLES = databaseTable(['ID'], ['TEXT PRIMARY KEY NOT NULL'])

DBT_PERMS_GUILD_ROLES = databaseTable(['ID'], ['TEXT PRIMARY KEY NOT NULL'])
