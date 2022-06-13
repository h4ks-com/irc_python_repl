#!/usr/bin/env python3
"""Python repl bot for irc using re-ircbot.

Indented to be executed on a docker container for better OPSEC
"""

import logging

import multiprocess
import requests
import RestrictedPython
from IrcBot.bot import Color, IrcBot, Message, utils
from IrcBot.utils import debug, log
from pathos.multiprocessing import ProcessPool
from RestrictedPython import (compile_restricted, limited_builtins,
                              safe_builtins, utility_builtins)
from RestrictedPython.PrintCollector import PrintCollector

##################################################
# SETTINGS                                       #
##################################################

LOGFILE = None
LEVEL = logging.INFO
HOST="10.0.0.252"
PORT=6667
SSL=False
NICK = 'pybot'
PASSWORD = ''
USERNAME = NICK
REALNAME = NICK
CHANNELS = ["#bots"]  # , "#lobby",]

utils.setPrefix("`")
utils.setParseOrderTopBottom(False)

MODULES_WHITELIST = ["numpy", "IrcBot", "math", "itertools", "socket", "time", "re", "random", "collections", "datetime", "requests", "http", "hashlib", "json", "copy", "functools", "secrets", "string"]
TIMEOUT = 5

##################################################
# LIB
##################################################

pool = ProcessPool(nodes=4)
user_source = {}
user_env = {}
user_state = {}
user_multiline = {}


def interpret(code, env):
    """Interprets the given python code inside a safe execution environment."""

    def guarded_import(mname, globals={}, locals={}, fromlist=(), # noqa A002
                       level=0):
        if mname in MODULES_WHITELIST or ("." in mname and mname.split(".")[0] in MODULES_WHITELIST):
            return __import__(mname, globals, locals, fromlist)
        else:
            raise Exception("This module is not whitelisted")

    code += "\n_ = printed"
    byte_code = compile_restricted(
        code,
        filename="<string>",
        mode="exec",
    )

    data = {
        "_print_": PrintCollector,
        "__builtins__": {
            **safe_builtins,
            **limited_builtins,
            **utility_builtins,
            "_getiter_": RestrictedPython.Eval.default_guarded_getiter,
            "_iter_unpack_sequence_": RestrictedPython.Guards.guarded_iter_unpack_sequence,
            "__import__": guarded_import,
            "abs": __builtins__.abs,
            "all": __builtins__.all, 
            "any": __builtins__.any,
            "ascii": __builtins__.ascii,
            "bin": __builtins__.bin,
            "bool": __builtins__.bool,
            "bytearray": __builtins__.bytearray,
            "bytes": __builtins__.bytes,
            "callable": __builtins__.callable,
            "chr": __builtins__.chr,
            "classmethod": __builtins__.classmethod,
            "complex": __builtins__.complex,
            "delattr": __builtins__.delattr,
            "dict": __builtins__.dict,
            "dir": __builtins__.dir,
            "divmod": __builtins__.divmod,
            "enumerate": __builtins__.enumerate,
            "filter": __builtins__.filter,
            "float": __builtins__.float,
            "format": __builtins__.format,
            "frozenset": __builtins__.frozenset,
            "getattr": __builtins__.getattr,
            "globals": __builtins__.globals,
            "hasattr": __builtins__.hasattr,
            "hash": __builtins__.hash,
            "help": __builtins__.help,
            "hex": __builtins__.hex,
            "id": __builtins__.id,
            "int": __builtins__.int,
            "isinstance": __builtins__.isinstance,
            "issubclass": __builtins__.issubclass,
            "iter": __builtins__.iter,
            "len": __builtins__.len,
            "list": __builtins__.list,
            "locals": __builtins__.locals,
            "map": __builtins__.map,
            "max": __builtins__.max,
            "min": __builtins__.min,
            "next": __builtins__.next,
            "object": __builtins__.object,
            "oct": __builtins__.oct,
            "ord": __builtins__.ord,
            "pow": __builtins__.pow,
            "print": __builtins__.print,
            "property": __builtins__.property,
            "range": __builtins__.range,
            "repr": __builtins__.repr,
            "reversed": __builtins__.reversed,
            "round": __builtins__.round,
            "set": __builtins__.set,
            "setattr": __builtins__.setattr,
            "slice": __builtins__.slice,
            "sorted": __builtins__.sorted,
            "staticmethod": __builtins__.staticmethod,
            "str": __builtins__.str,
            "sum": __builtins__.sum,
            "super": __builtins__.super,
            "tuple": __builtins__.tuple,
            "type": __builtins__.type,
            "vars": __builtins__.vars,
            "zip": __builtins__.zip,
        },
        "_getattr_": RestrictedPython.Guards.safer_getattr,
        "_write_": lambda x: x,
        "_getitem_": lambda obj, key: obj[key]
    }
    debug("!!!!! Executing command from process.......")
    debug(str(env))
    exec(byte_code, data, env)
    debug("-" * 23)
    debug(str(env))
    return env

def process_source(nick, source):
    global user_source
    debug("Starting process")
    if nick not in user_env:
        user_env[nick] = {}
    if nick not in user_source:
        user_source[nick] = ""
    debug("Checked user env")
    result = pool.apipe(interpret, source, user_env[nick])
    output = None
    debug("Launched interpret process")
    try:
        debug("Collecting output")
        env = result.get(timeout=TIMEOUT)
        output = env["_"]
        user_env[nick] = env
        user_source[nick] += "\n" + source
        debug("Output collected")
    except multiprocess.context.TimeoutError:
        output = Color(
            "Timeout error - do you have an infinite loop?", fg=Color.red).str
    except Exception as e:
        output = Color("Runtime error: {}".format(e), fg=Color.red).str

    return output or "(no output to stdout)"

##################################################
# RUNTIME & HANDLERS
##################################################

@utils.arg_command("clear", "Clear environment and history")
def clear(args, message):
    if message.nick in user_source:
        log("Clearing ", message.nick)
        user_source[message.nick] = ""
        user_env[message.nick] = {}
        return f"<{message.nick}> Environment and history cleared!"


@utils.regex_cmd_with_messsage("^`(.+)`$")
async def run(bot: IrcBot, m, message):
    global pool
    global user_source
    source = m[1]
    debug("Executing {}".format(repr(source)))
    output = process_source(message.nick, source)
    await bot.send_message(f"<{message.nick}>> " + output, message.channel)

@utils.regex_cmd_with_messsage("^(.+)$")
def multiline_capture(m, message):
    global user_multiline
    debug(f"RECEIVED: {message.text=}")
    if message.nick in user_state and user_state[message.nick]:
        if message.nick not in user_multiline:
            user_multiline[message.nick] = ""
        user_multiline[message.nick] += message.text + "\n"

@utils.regex_cmd_with_messsage("^```$")
def start_multiline(m, message):
    global user_state
    if message.nick not in user_state or not user_state[message.nick]:
        user_state[message.nick] = True
        user_multiline[message.nick] = ""
        return f"<{message.nick}> Waiting for lines, type ``` to finish and execute"
    else:
        user_state[message.nick] = False
        if message.nick not in user_multiline or (
                message.nick in user_multiline and len(user_multiline[message.nick]) == 0):
            return f"<{message.nick}> Ignoring empty multiline code"
        output = process_source(message.nick, user_multiline[message.nick])
        return f"<{message.nick}>> " + output


@utils.arg_command("lsmod", "List available whitelisted modules")
def lsmod(args, message):
    return f"<{message.nick}> Available modules are: " + ", ".join(MODULES_WHITELIST)

@utils.arg_command("paste", "Paste the code history to ix.io")
def paste(args, message):
    if message.nick not in user_source:
        return
    log("Pasting ", message.nick)
    url = "http://ix.io"
    payload = {'f:N': user_source[message.nick],
               'name:N': 'python_repl_bot_dump.py'}
    response = requests.request("POST", url, data=payload)
    return f"<{message.nick}> " + response.text

@utils.arg_command("show", "Sends the code history over private messages")
def show(args, message):
    if message.nick not in user_source:
        return
    log("Showing in PM ", message.nick)
    return [Message(message=ln, channel=message.nick) for ln in user_source[message.nick].split("\n")]

@utils.arg_command("run", "Runs code from a url, e.g. ix.io")
def paste_run(args, message):
    if not args[1]:
        return f"<{message.nick}> This commands requires an argument!"
    log("Running thing", message.nick)
    response = requests.get(args[1])
    if response.status_code != 200:
        return f"<{message.nick}> Failed to fetch this url!"
    source = response.content.decode().strip()
    debug("Executing {}".format(repr(source)))
    output = process_source(message.nick, source)
    return f"<{message.nick}>> " + output

@utils.arg_command("get", "Gets the environmental variables from another user in the chat")
async def transfer(bot: IrcBot, args, message):
    if not args[1]:
        await bot.send_message(f"<{message.nick}> This commands requires an argument!", message.channel)
        return
    names = await bot.list_names(message.channel)
    if args[1] not in names:
        await bot.send_message(f"<{message.nick}> This user is not on this channel", message.channel)
        return
    if args[1] not in user_env:
        await bot.send_message(f"<{message.nick}> This user does not have an environment started", message.channel)
        return
    nick = message.nick
    if nick not in user_env:
        user_env[nick] = {}
    user_env[nick].update(user_env[args[1]])
    await bot.send_message(f"<{message.nick}> Environment imported!", message.channel)

if __name__ == "__main__":
    utils.setLogging(LEVEL, LOGFILE)
    bot = IrcBot(HOST, PORT, NICK, CHANNELS, PASSWORD, strip_messages=False, use_ssl=SSL)
    bot.run()
