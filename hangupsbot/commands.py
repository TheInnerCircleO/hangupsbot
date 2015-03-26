import sys, json, random, asyncio
import time
import hangups

from datetime import date as datetime
from hangups.ui.utils import get_conv_name
from hangupsbot.utils import text_to_segments

from random import randint
import re


class CommandDispatcher(object):
    """Register commands and run them"""
    def __init__(self):
        self.commands = {}
        self.unknown_command = None

    @asyncio.coroutine
    def run(self, bot, event, *args, **kwds):
        """Run command"""
        try:
            func = self.commands[args[0]]
        except KeyError:
            if self.unknown_command:
                func = self.unknown_command
            else:
                raise

        # Automatically wrap command function in coroutine
        # (so we don't have to write @asyncio.coroutine decorator before every command function)
        func = asyncio.coroutine(func)

        args = list(args[1:])

        try:
            yield from func(bot, event, *args, **kwds)
        except Exception as e:
            print(e)

    def register(self, func):
        """Decorator for registering command"""
        self.commands[func.__name__] = func
        return func

    def register_unknown(self, func):
        """Decorator for registering unknown command"""
        self.unknown_command = func
        return func

# CommandDispatcher singleton
command = CommandDispatcher()


@command.register_unknown
def unknown_command(bot, event, *args):
    """Unknown command handler"""
    bot.send_message(event.conv, 'English mother fucker. Do you speak it?')


@command.register
def help(bot, event, cmd=None, *args):
    """Help me, Obi-Wan Kenobi. You're my only hope."""
    if not cmd:
        segments = [hangups.ChatMessageSegment('My available commands:', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(', '.join(sorted(command.commands.keys())))]
    else:
        try:
            command_fn = command.commands[cmd]
            segments = [hangups.ChatMessageSegment('{}:'.format(cmd), is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            segments.extend(text_to_segments(command_fn.__doc__))
        except KeyError:
            yield from command.unknown_command(bot, event)
            return

    bot.send_message_segments(event.conv, segments)


@command.register
def ping(bot, event, *args):
    """Zahrajem ping pong!"""
    bot.send_message(event.conv, 'pong')


@command.register
def echo(bot, event, *args):
    """Let Ape!"""
    bot.send_message(event.conv, '{}'.format(' '.join(args)))


@command.register
def users(bot, event, *args):
    """Listing all users in the current hangout (including G + accounts and emails)"""
    segments = [hangups.ChatMessageSegment('Users in chat ({}):'.format(len(event.conv.users)),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    for u in sorted(event.conv.users, key=lambda x: x.full_name.split()[-1]):
        link = 'https://plus.google.com/u/0/{}/about'.format(u.id_.chat_id)
        segments.append(hangups.ChatMessageSegment(u.full_name, hangups.SegmentType.LINK,
                                                   link_target=link))
        if u.emails:
            segments.append(hangups.ChatMessageSegment(' ('))
            segments.append(hangups.ChatMessageSegment(u.emails[0], hangups.SegmentType.LINK,
                                                       link_target='mailto:{}'.format(u.emails[0])))
            segments.append(hangups.ChatMessageSegment(')'))
        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
    bot.send_message_segments(event.conv, segments)


@command.register
def user(bot, event, username, *args):
    """Find people by name"""
    username_lower = username.strip().lower()
    segments = [hangups.ChatMessageSegment('Here are the users I could find "{}":'.format(username),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    for u in sorted(bot._user_list._user_dict.values(), key=lambda x: x.full_name.split()[-1]):
        if not username_lower in u.full_name.lower():
            continue

        link = 'https://plus.google.com/u/0/{}/about'.format(u.id_.chat_id)
        segments.append(hangups.ChatMessageSegment(u.full_name, hangups.SegmentType.LINK,
                                                   link_target=link))
        if u.emails:
            segments.append(hangups.ChatMessageSegment(' ('))
            segments.append(hangups.ChatMessageSegment(u.emails[0], hangups.SegmentType.LINK,
                                                       link_target='mailto:{}'.format(u.emails[0])))
            segments.append(hangups.ChatMessageSegment(')'))
        segments.append(hangups.ChatMessageSegment(' ... {}'.format(u.id_.chat_id)))
        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
    bot.send_message_segments(event.conv, segments)


@command.register
def hangouts(bot, event, *args):
    """Listing all active hangouts in which battered shoes
         Explanation: c ... commands, f ... forwarding, and ... autoreplies"""
    segments = [hangups.ChatMessageSegment('Hangous I am in:', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    for c in bot.list_conversations():
        s = '{} [c: {:d}, f: {:d}, a: {:d}]'.format(get_conv_name(c, truncate=True),
                                                    bot.get_config_suboption(c.id_, 'commands_enabled'),
                                                    bot.get_config_suboption(c.id_, 'forwarding_enabled'),
                                                    bot.get_config_suboption(c.id_, 'autoreplies_enabled'))
        segments.append(hangups.ChatMessageSegment(s))
        segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))

    bot.send_message_segments(event.conv, segments)


@command.register
def rename(bot, event, *args):
    """Renames the current Hangout"""
    yield from bot._client.setchatname(event.conv_id, ' '.join(args))


@command.register
def leave(bot, event, conversation=None, *args):
    """Exits the current or other specified Hangout"""
    convs = []
    if not conversation:
        convs.append(event.conv)
    else:
        conversation = conversation.strip().lower()
        for c in bot.list_conversations():
            if conversation in get_conv_name(c, truncate=True).lower():
                convs.append(c)

    for c in convs:
        yield from c.send_message([
            hangups.ChatMessageSegment('I\'ll be back.')
        ])
        yield from bot._conv_list.delete_conversation(c.id_)


@command.register
def easteregg(bot, event, easteregg, eggcount=1, period=0.5, *args):
    """Starts combo Easter eggs (parameters: egg [number] [period]))
       Supported Easter Eggs: ponies, pitchforks, bikeshed, shydino"""
    for i in range(int(eggcount)):
        yield from bot._client.sendeasteregg(event.conv_id, easteregg)
        if int(eggcount) > 1:
            yield from asyncio.sleep(float(period) + random.uniform(-0.1, 0.1))

@command.register
def spoof(bot, event, *args):
    """Spoofne IngressBota instance on the specified coordinates"""
    segments = [hangups.ChatMessageSegment('!!! CAUTION !!!', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    segments.append(hangups.ChatMessageSegment('User {} ('.format(event.user.full_name)))
    link = 'https://plus.google.com/u/0/{}/about'.format(event.user.id_.chat_id)
    segments.append(hangups.ChatMessageSegment(link, hangups.SegmentType.LINK,
                                               link_target=link))
    segments.append(hangups.ChatMessageSegment(') has just reported on Niantic for attempted spoofing!'))
    bot.send_message_segments(event.conv, segments)


@command.register
def reload(bot, event, *args):
    """Reloads the configuration of the boot file"""
    bot.config.load()


@command.register
def quit(bot, event, *args):
    """Let shoe live!"""
    print('HangupsBot killed by user {} from conversation {}'.format(event.user.full_name,
                                                                     get_conv_name(event.conv, truncate=True)))
    yield from bot._client.disconnect()


@command.register
def config(bot, event, cmd=None, *args):
    """Displays or modifies the configuration boot
        Parameters: /bot config [get|set] [key] [subkey] [...] [value]"""

    if cmd == 'get' or cmd is None:
        config_args = list(args)
        value = bot.config.get_by_path(config_args) if config_args else dict(bot.config)
    elif cmd == 'set':
        config_args = list(args[:-1])
        if len(args) >= 2:
            bot.config.set_by_path(config_args, json.loads(args[-1]))
            bot.config.save()
            value = bot.config.get_by_path(config_args)
        else:
            yield from command.unknown_command(bot, event)
            return
    else:
        yield from command.unknown_command(bot, event)
        return

    if value is None:
        value = 'Parameter does not exist!'

    config_path = ' '.join(k for k in ['config'] + config_args)
    segments = [hangups.ChatMessageSegment('{}:'.format(config_path),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    segments.extend(text_to_segments(json.dumps(value, indent=2, sort_keys=True)))
    bot.send_message_segments(event.conv, segments)


def _random_date(start, end, format):
    stime = time.mktime(time.strptime(start, format))
    etime = time.mktime(time.strptime(end, format))
    ptime = stime + random.random() * (etime - stime)
    return time.strftime(format, time.localtime(ptime))


@command.register
def dilbert(bot, event, *args):
    """First dilbert 1989-04-16"""
    dilbert_modifier = ''
    for arg in list(args):
        if arg == 'random':
            dilbert_date_format = '%Y-%m-%d'
            today = datetime.today().strftime(dilbert_date_format)
            dilbert_modifier = _random_date(
                '1989-04-16',
                today,
                dilbert_date_format)

    dilbert_link = 'http://dilbert.com/{}'.format(dilbert_modifier)
    message = "Here's your fucking dilbert, {}".format(dilbert_link)
    bot.parse_and_send_segments(event.conv, message)

@command.register
def slap(bot, event, name):
    message = "/me slaps {} around a bit with a large black cock".format(name)
    bot.parse_and_send_segments(event.conv, message)

@command.register
def roll(bot, event, *args):

    for arg in list(args):

        validArg = re.match('[0-9]*d[0-9]*', arg)

        if validArg is None:
            bot.send_message(event.conv, 'Invalid dice string: {}'.format(arg))
            continue

        i = 1
        die = int(arg.split('d')[0])
        sides  = int(arg.split('d')[1])
        results = ''
        total = 0

        while (i <= die):
            roll = randint(1, sides)
            results += str(roll) if i == 1 else ', ' + str(roll)
            total += roll
            i += 1

        bot.send_message(event.conv, 'Rolling {}: {} ({})'.format(arg, results, total))
