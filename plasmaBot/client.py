import sys
import asyncio
import aiohttp
import websockets

import discord
import traceback

from plasmaBot.utils import Printer, Shutdown, Restart, ErrorRestart
from plasmaBot.config import Config
from plasmaBot.permissions import Permissions
from plasmaBot.logger import Logger
from plasmaBot.terminal import Terminal

from plasmaBot.pl_man import PluginManager


class Client(discord.AutoShardedClient):
    """Client Class:  Extension of discord.AutoShardedClient for automatic shard support."""

    def __init__(self, printer=None):
        """Initiate Bot Class and Included Attributes"""

        super().__init__() # Initiate Standard Client

        if printer is None:
            self.printer = Printer(self)
        else:
            printer.ref_client(self)
            self.printer = printer

        self.ready = False
        self.queue = asyncio.Queue()

        self.loop.add_reader(sys.stdin, self.on_terminal, self.queue)
        self.bot_messages = {}

        self.config = Config(self)
        self.permissions = Permissions(self)
        self.logger = Logger(self)
        self.terminal = Terminal(self)

        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_all()

        self.version = '5.0.0a1'
        self.branch = 'BETA'

        self.shutdown_state = False
        self.restart_state = False

        #############################
        #   CLIENT HELPER METHODS   #
        #############################

    @asyncio.coroutine
    def _connect(self):
        """Custom connection scripts to handle shutdown and restart commands and exceptions"""
        yield from self.launch_shards()

        while True:
            if self.shutdown_state == True:
                raise Shutdown
            elif self.restart_state == True:
                raise Restart
            else:
                pollers = [shard.get_future() for shard in self.shards.values()]
                done, pending = yield from asyncio.wait(pollers, loop=self.loop, return_when=asyncio.FIRST_COMPLETED)
                for f in done:
                    # we wanna re-raise to the main Client.connect handler if applicable
                    f.result()

    @asyncio.coroutine
    def _run_event(self, coro, event_name, *args, **kwargs):
        """Custom Event Script that additionally sends events through to the plugin manager for distribution amoung plugins"""
        try:
            yield from coro(*args, **kwargs)
            yield from self.plugin_manager.run_event(event_name, *args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                yield from self.on_error(event_name, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    def initiate(self):
        """Start PlasmaBot and login to discord servers."""
        self.printer.indicate('Initiating Connection to Discord...', cmd=False)

        try:
            self.loop.run_until_complete(self.start(self.config['token']))

        except discord.errors.LoginFailure:
            self.printer.warning('ERROR: Cannot log in to Discord due to Invalid Credentials.')
            self.printer.explain('\nPlease check credentials and try again.', cmd=False)
            raise Shutdown

        except (Shutdown, Restart, ErrorRestart):
            raise

        except Exception:
            self.printer.warning('ERROR: Cannot log in or reconnect to Discord.')
            self.printer.explain('This may be caused by network issues or malfunctioning SSL.')
            self.printer.explain('The bot will attempt to reconnect to the discord servers until manually overriden in case this issue is temporary.')
            raise Restart

    def shutdown(self):
        """Shutdown the Bot."""
        self.shutdown_state = True

    def restart(self):
        """Restart the Bot."""
        self.restart_state = True

    async def set_presence(self):
        """Set the presence of the bot using `change_presence` based of config items."""
        game_text = self.config['presence']['game']

        if '<name>' in game_text.lower():
            game_text = game_text.replace('<name>', self.config['presence']['name'])

        if '<prefix>' in game_text.lower():
            game_text = game_text.replace('<prefix>', self.config['presence']['prefix'])

        if '<s_count>' in game_text.lower():
            game_text = game_text.replace('<s_count>', str(len(self.guilds)))

        if '<s_plural>' in game_text.lower():
            if len(self.guilds) > 1:
                game_text = game_text.replace('<s_plural>', 's')
            else:
                game_text = game_text.replace('<s_plural>', '')

        status_text = self.config['presence']['status']

        if status_text.lower() == 'online':
            status = discord.Status.online
        elif status_text.lower() == 'idle':
            status = discord.Status.idle
        elif status_text.lower() == 'dnd' or status_text.lower() == 'do_not_disturb' or status_text.lower() == 'do not disturb':
            status = discord.Status.dnd
        elif status_text.lower() == 'invisible':
            status = discord.Status.invisible
        else:
            status = discord.Status.online

        if not status == discord.Status.invisible:
            if self.config['presence']['stream']['enabled']:
                game = discord.Game(name=game_text, url=self.config['presence']['stream']['url'], type=1)
                await self.change_presence(game=game)
            else:
                game = discord.Game(name=game_text)
                await self.change_presence(game=game, status=status)
        else:
            await self.change_presence(status=status)


           #######################
           #   TERMINAL EVENTS   #
           #######################

    def on_terminal(self, queue):
        input_msg = sys.stdin.readline().strip()
        prefix = self.config['terminal']['prefix']

        if input_msg != '':
            if self.terminal.enabled and self.ready:
                if input_msg.lower().startswith(prefix) and not (input_msg.lower() == prefix or input_msg.lower == ' {}'.format(prefix)):
                    asyncio.ensure_future(self.on_terminal_command(input_msg))
                else:
                    asyncio.ensure_future(self.on_terminal_message(input_msg))
            else:
                self.printer.warning('Terminal Interface Disabled.')
        else:
            self.printer.cmd_return()

    async def on_terminal_command(self, message):
        await self.plugin_manager.fire_terminal_command(message)

    async def on_terminal_message(self, message):
        if self.terminal.messaging:
            self.printer.indicate('\033[F\033[F', tag=0)
            if not self.terminal.channel.id in self.terminal.messages:
                self.terminal.messages[self.terminal.channel.id] = []
            self.terminal.messages[self.terminal.channel.id] += [await self.terminal.channel.send(message)]
        else:
            self.printer.warning('Terminal Messaging Disabled.')


            #####################
            #   CLIENT EVENTS   #
            #####################

    async def on_error(self, event_method, *args, **kwargs):
        """Custom Error Handler to allow for Shutdown and Restart signals to work properly to work properly."""
        exception = sys.exc_info()
        traceback_str = traceback.format_exc()
        if exception[0] == Shutdown:
            self.shutdown()
        elif exception[0] == Restart:
            self.restart()
        else:
            self.printer.warning('Ignoring Exception in {}:\n\n{}'.format(event_method, traceback_str))

    async def on_shard_ready(self, shard_id):
        """Aknowledge the connection of a specific shard upon connection."""
        self.printer.success('{} Shard #{} Connected to Discord!'.format(self.config['presence']['name'], shard_id))

    async def on_ready(self):
        """Aknowledge the initial reddiness of the bot upon first connection."""
        self.ready = True
        await self.set_presence()
        await self.logger.initialize_log_channels()
        await self.terminal.detect_channel()

    async def on_guild_join(self, guild):
        """Event Fired upon joining a Guild."""
        await self.set_presence()
        await self.terminal.detect_channel()

    async def on_guild_remove(self, guild):
        """Event Fired upon leaving a Guild."""
        await self.set_presence()
        await self.terminal.detect_channel()

    async def on_message(self, message):
        """Event Fired each time the client recieves record of a Message"""
        await self.terminal.display_message(message)
