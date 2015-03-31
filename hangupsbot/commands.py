import asyncio
import hangups
import json
import random
import re
import requests
import time

from datetime import date as datetime

from hangups.ui.utils import get_conv_name
from hangupsbot.utils import text_to_segments

from random import randint


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
        # (so we don't have to write @asyncio.coroutine decorator
        # before every command function)
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
        segments = [
            hangups.ChatMessageSegment(
                'My available commands:',
                is_bold=True),
            hangups.ChatMessageSegment(
                '\n',
                hangups.SegmentType.LINE_BREAK),
            hangups.ChatMessageSegment(
                ', '.join(sorted(command.commands.keys())))]

    else:
        try:
            command_fn = command.commands[cmd]
            segments = [
                hangups.ChatMessageSegment(
                    '{}:'.format(cmd),
                    is_bold=True),
                hangups.ChatMessageSegment(
                    '\n',
                    hangups.SegmentType.LINE_BREAK)]

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
    """
    Listing all users in the current hangout
    (including G + accounts and emails)
    """

    segments = [
        hangups.ChatMessageSegment(
            'Users in chat ({}):'.format(len(event.conv.users)),
            is_bold=True),
        hangups.ChatMessageSegment(
            '\n',
            hangups.SegmentType.LINE_BREAK)]

    for u in sorted(event.conv.users, key=lambda x: x.full_name.split()[-1]):
        link = 'https://plus.google.com/u/0/{}/about'.format(u.id_.chat_id)
        segments.append(
            hangups.ChatMessageSegment(
                u.full_name,
                hangups.SegmentType.LINK,
                link_target=link))

        if u.emails:
            segments.append(
                hangups.ChatMessageSegment(
                    ' ('))
            segments.append(
                hangups.ChatMessageSegment(
                    u.emails[0],
                    hangups.SegmentType.LINK,
                    link_target='mailto:{}'.format(u.emails[0])))
            segments.append(hangups.ChatMessageSegment(')'))

        segments.append(
            hangups.ChatMessageSegment(
                '\n',
                hangups.SegmentType.LINE_BREAK))

    bot.send_message_segments(event.conv, segments)


@command.register
def user(bot, event, username, *args):
    """Find people by name"""
    username_lower = username.strip().lower()
    segments = [
        hangups.ChatMessageSegment(
            'Here are the users I could find "{}":'.format(username),
            is_bold=True),
        hangups.ChatMessageSegment(
            '\n',
            hangups.SegmentType.LINE_BREAK)]

    for u in sorted(
            bot._user_list._user_dict.values(),
            key=lambda x: x.full_name.split()[-1]):

        if username_lower not in u.full_name.lower():
            continue

        link = 'https://plus.google.com/u/0/{}/about'.format(u.id_.chat_id)
        segments.append(
            hangups.ChatMessageSegment(
                u.full_name,
                hangups.SegmentType.LINK,
                link_target=link))
        if u.emails:
            segments.append(hangups.ChatMessageSegment(
                ' ('))
            segments.append(hangups.ChatMessageSegment(
                u.emails[0],
                hangups.SegmentType.LINK,
                link_target='mailto:{}'.format(u.emails[0])))
            segments.append(hangups.ChatMessageSegment(')'))
        segments.append(
            hangups.ChatMessageSegment(
                ' ... {}'.format(u.id_.chat_id)))
        segments.append(
            hangups.ChatMessageSegment(
                '\n',
                hangups.SegmentType.LINE_BREAK))

    bot.send_message_segments(event.conv, segments)


@command.register
def hangouts(bot, event, *args):
    """Listing all active hangouts in which battered shoes
         Explanation: c ... commands, f ... forwarding, and ... autoreplies"""
    segments = [
        hangups.ChatMessageSegment(
            'Hangous I am in:',
            is_bold=True),
        hangups.ChatMessageSegment(
            '\n',
            hangups.SegmentType.LINE_BREAK)]

    for c in bot.list_conversations():
        s = '{} [c: {:d}, f: {:d}, a: {:d}]'.format(
            get_conv_name(c, truncate=True),
            bot.get_config_suboption(c.id_, 'commands_enabled'),
            bot.get_config_suboption(c.id_, 'forwarding_enabled'),
            bot.get_config_suboption(c.id_, 'autoreplies_enabled'))

        segments.append(
            hangups.ChatMessageSegment(s))
        segments.append(hangups.ChatMessageSegment(
            '\n',
            hangups.SegmentType.LINE_BREAK))

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
    # Make a value to check against, don't want hours of spam in chat
    spam_count = float(eggcount) * float(period)
    if spam_count > 15:
        eggcount = 1

    for i in range(int(eggcount)):
        yield from bot._client.sendeasteregg(event.conv_id, easteregg)
        if int(eggcount) > 1:
            yield from asyncio.sleep(float(period) + random.uniform(-0.1, 0.1))


@command.register
def spoof(bot, event, *args):
    """Spoofne IngressBota instance on the specified coordinates"""
    segments = [
        hangups.ChatMessageSegment(
            '!!! CAUTION !!!',
            is_bold=True),
        hangups.ChatMessageSegment(
            '\n',
            hangups.SegmentType.LINE_BREAK)]

    segments.append(
        hangups.ChatMessageSegment(
            'User {} ('.format(event.user.full_name)))

    link = 'https://plus.google.com/u/0/{}/about'.format(
        event.user.id_.chat_id)

    segments.append(hangups.ChatMessageSegment(
        link,
        hangups.SegmentType.LINK,
        link_target=link))
    segments.append(
        hangups.ChatMessageSegment(
            ') has just reported on Niantic for attempted spoofing!'))

    bot.send_message_segments(event.conv, segments)


@command.register
def reload(bot, event, *args):
    """Reloads the configuration of the boot file"""
    bot.config.load()


@command.register
def quit(bot, event, *args):
    """Let shoe live!"""
    print(
        'HangupsBot killed by user {} from conversation {}'.format(
            event.user.full_name,
            get_conv_name(event.conv, truncate=True)))
    yield from bot._client.disconnect()


@command.register
def config(bot, event, cmd=None, *args):
    """Displays or modifies the configuration boot
        Parameters: /bot config [get|set] [key] [subkey] [...] [value]"""

    if cmd == 'get' or cmd is None:
        config_args = list(args)
        if config_args:
            value = bot.config.get_by_path(config_args)
        else:
            value = dict(bot.config)

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
    segments = [
        hangups.ChatMessageSegment(
            '{}:'.format(config_path),
            is_bold=True),
        hangups.ChatMessageSegment(
            '\n',
            hangups.SegmentType.LINE_BREAK)]

    segments.extend(
        text_to_segments(
            json.dumps(value, indent=2, sort_keys=True)))
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

    segments = list()

    for arg in list(args):

        validArg = re.match('[0-9]*d[0-9]*', arg)

        if validArg is None:
            bot.send_message(event.conv, 'Invalid dice string: {}'.format(arg))
            continue

        segments.append(
            hangups.ChatMessageSegment(
                'Rolling {}: '.format(arg),
                is_bold=True
            )
        )

        total = 0

        die = int(arg.split('d')[0])
        sides = int(arg.split('d')[1])

        for i in range(1, die + 1):

            roll = randint(1, sides)

            if i != 1:
                segments.append(hangups.ChatMessageSegment(', '))

            segments.append(hangups.ChatMessageSegment(str(roll)))

            total += roll

        segments.append(hangups.ChatMessageSegment(' [{}]'.format(total)))

        segments.append(
            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)
        )

    bot.send_message_segments(event.conv, segments)


def get_json(url):
    """
    TODO: Make this act sane when bad status_code or an Exception is thrown
    Grabs json from a URL and returns a python dict
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; \
               rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11'}

    json_result = requests.get(url, headers=headers)
    if json_result.status_code == 200:
        try:
            obj_result = json.loads(json_result.text)
            return obj_result
        except Exception as e:
            return e
    else:
        return json_result.status_code


def get_random_topic(seed):

    # Safe it
    re.sub(r'\W+', '', seed)

    url = 'http://www.reddit.com/search.json?q=%s' % seed

    try:

        obj_results = get_json(url)

        total_results = len(obj_results['data']['children']) - 1
        rand_index = randint(0, min([total_results, 5]))

        topic_obj = obj_results['data']['children'][rand_index]

        return topic_obj

    except:

        return "Hmmm."


@command.register
def stock(bot, event, *args):
    """
    /bot stock ticker1 ticker2 tickerN
    displays current price for tickers
    """
    segments = []
    tickers = ','.join(list(args))
    raw_data = requests.get(
        'http://finance.google.com/finance/info?client=ig&q=' +
        tickers)
    try:
        # Cant use get_json because of 3 invalid chars
        data = json.loads(raw_data.text[3:])
        for i in data:
            stock_link = 'https://www.google.com/finance?q={}'.format(i['t'])
            link_segment = hangups.ChatMessageSegment(
                '{:<6}'.format(i['t']),
                hangups.SegmentType.LINK,
                link_target=stock_link
            )
            text = ': {:<5} | {:^4} ({}%)'.format(i['l'], i['c'], i['cp'])
            segments.append(link_segment)
            segments.append(hangups.ChatMessageSegment(text))
            segments.append(
                hangups.ChatMessageSegment(
                    '\n',
                    hangups.SegmentType.LINE_BREAK
                )
            )
    except Exception as e:
        return bot.parse_and_send_segments(e)

    bot.send_message_segments(event.conv, segments)


@command.register
def btc(bot, event, *args):
    """
    /bot btc
    displays current btc on BTC-e
    """
    btce_json = get_json('http://btc-e.com/api/3/ticker/btc_usd')
    result = 'BTC/USD: ' + str(btce_json['btc_usd']['avg'])
    bot.parse_and_send_segments(event.conv, result)


@command.register
def thoughts(bot, event, *args):

    seed = ' '.join(args)
    topic = get_random_topic(seed)

    rerep = re.compile(re.escape('reddit'), re.IGNORECASE)

    title = rerep.sub(
        'The Inner Circle',
        topic['data']['title']
    )

    link = 'https://www.reddit.com{}'.format(topic['data']['permalink'])

    segments = [
        hangups.ChatMessageSegment(
            title,
            hangups.SegmentType.LINK,
            link_target=link
        )
    ]

    bot.send_message_segments(event.conv, segments)


@command.register
def xkcd(bot, event, *args):

    xkcdObj = get_json('http://xkcd.com/info.0.json')

    if args:
        if args[0] == 'random':
            xkcdObj = get_json(
                'http://xkcd.com/%s/info.0.json' % randint(
                    1,
                    xkcdObj['num']))

        elif re.match('^\d*$', args[0]):
            if int(args[0]) <= xkcdObj['num'] and int(args[0]) >= 1:
                xkcdObj = get_json('http://xkcd.com/%s/info.0.json' % args[0])
            else:
                bot.parse_and_send_segments(
                    event.conv,
                    'ERROR: Comic number out of range')
                return

        else:
            bot.parse_and_send_segments(
                event.conv,
                'ERROR: Invalid comic number')
            return

    text = '{}: http://xkcd.com/{}'.format(
        xkcdObj['safe_title'],
        xkcdObj['num'])

    bot.parse_and_send_segments(event.conv, text)


@command.register
def prs(bot, event, *args):

    prs = get_json(
        'https://api.github.com/repos/TheInnerCircleO/hangupsbot/pulls'
    )

    if not prs:
        bot.parse_and_send_segments(event.conv, 'No open pull requests')
        return

    segments = [
        hangups.ChatMessageSegment('Open pull requests:', is_bold=True)
    ]

    for pr in prs:
        segments.append(
            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)
        )

        segments.append(
            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)
        )

        segments.append(
            hangups.ChatMessageSegment('[{}] '.format(pr['number']))
        )

        segments.append(
            hangups.ChatMessageSegment(
                pr['title'],
                hangups.SegmentType.LINK,
                link_target=pr['html_url']
            )
        )

        segments.append(hangups.ChatMessageSegment(' by '))

        segments.append(
            hangups.ChatMessageSegment(
                pr['user']['login'],
                hangups.SegmentType.LINK,
                link_target=pr['user']['url']
            )
        )

    bot.send_message_segments(event.conv, segments)
