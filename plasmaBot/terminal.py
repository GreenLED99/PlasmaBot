"""Class that stores information about the terminal bot interface for use within Bot Commands and Operations"""

import re

import discord


class Terminal(object):
    """Class that stores information about the terminal bot interface for use within Bot Commands and Operations"""

    def __init__(self, client):
        self.client = client
        self.config = client.config
        self.printer = client.printer

        self.enabled = False

        self.messaging = False
        self.channel = None
        self.guild = None
        self.guild_member = None

        self.messages = {}

        self.single_backtick_regex = r'(?<!`)`(?P<contents>[^`]{1,})`(?!`)'
        self.single_backtick_substring = self.printer.Back.MAGENTA + self.printer.Fore.WHITE + self.printer.Style.BRIGHT + '\g<contents>' + self.printer.Style.RESET_ALL
        self.tripple_backtick_regex = r'(?<!`)`{3}(?P<contents>[^`]{1,})`{3}(?!`)'
        self.tripple_backtick_substring = '\n' + self.printer.Back.MAGENTA + self.printer.Fore.WHITE + '\g<contents>' + self.printer.Style.RESET_ALL + '\n'

    async def detect_channel(self):
        """Detect the terminal attached channel and register it for future use"""
        if self.config['terminal']['enabled']:
            self.enabled = True
        else:
            self.enabled = False

        if self.config['terminal']['messaging']:
            self.messaging = True

            channel_id = int(self.config['terminal']['channel'])
            self.channel = self.client.get_channel(channel_id)

            if not self.channel:
                try:
                    user = await self.client.get_user_info(channel_id)
                except:
                    user = None

                if user:
                    if not user.dm_channel:
                        await user.create_dm()
                    self.channel = user.dm_channel

            if isinstance(self.channel, discord.abc.GuildChannel):
                self.guild = self.channel.guild
                self.guild_member = self.guild.me
            else:
                self.guild = None
                self.guild_member = None

            if not self.channel:
                self.messaging = False
                terminal = self.config['terminal']
                terminal['messaging'] = False
                self.config['terminal'] = terminal

                self.printer.warning('Terminal Channel Not Found, Disabling Terminal Messaging...')
                return
            else:
                self.printer.success('Joined {}'.format('#{} in {}'.format(self.channel.name, self.guild.name) if self.guild else 'Direct Message with {}'.format(self.channel.recipient.display_name)))
        else:
            self.messaging = False
            self.channel = None
            self.guild = None
            self.guild_user = None

    async def display_message(self, message):
        """Write Message Contents to the Terminal for user viewing"""
        if not self.client.ready:
            return

        if self.messaging and not message.channel == self.channel:
            return

        content = str(message.content).strip()

        if len(message.embeds) >= 1:
            content += ' [Embed Attached]'

        for user in message.mentions:
            if not user == self.client.user:
                content = content.replace('<@!{}>'.format(user.id), '{}@{}{}'.format(self.printer.Back.CYAN + self.printer.Fore.WHITE, user.display_name, self.printer.Style.RESET_ALL))
            else:
                content = content.replace('<@!{}>'.format(user.id), '{}@{}{}'.format(self.printer.Back.CYAN + self.printer.Fore.MAGENTA, user.display_name, self.printer.Style.RESET_ALL))

        for role in message.role_mentions:
            content = content.replace('<@&{}>'.format(role.id), '{}@{}{}'.format(self.printer.Back.GREEN + self.printer.Fore.WHITE, role.name, self.printer.Style.RESET_ALL))

        for channel in message.channel_mentions:
            content = content.replace('<#{}>'.format(channel.id), '{}@{}{}'.format(self.printer.Back.YELLOW + self.printer.Fore.WHITE, channel.name, self.printer.Style.RESET_ALL))

        content = re.sub(self.single_backtick_regex, self.single_backtick_substring, content, 0)
        content = re.sub(self.tripple_backtick_regex, self.tripple_backtick_substring, content, 0)

        content = content.strip().replace('\n', '\n                ')

        content = self.printer.Back.BLACK + self.printer.Fore.MAGENTA + '[MESSAGE]' + self.printer.Style.RESET_ALL + ' ' + content

        content += ' ~ {}#{} ({} '.format(message.author.name, message.author.discriminator, message.author.display_name)

        if isinstance(message.channel, discord.abc.PrivateChannel):
            content += 'via Direct Message)'
        else:
            content += 'in #{} of {})'.format(message.channel.name, message.channel.guild.name)

        self.printer.indicate(content)
