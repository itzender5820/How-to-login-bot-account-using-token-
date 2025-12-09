#!/usr/bin/env python3
"""
maya_cli.py - Discord CLI "OS" for Termux
Author: generated for you
Bot display name: Maya

INSTRUCTIONS:
 - Edit TOKEN below and save.
 - Run: python maya_cli.py
 - Use 'help' inside for commands.
"""

import discord
import threading
import asyncio
import time
import os
import sys

# ---------------- USER CONFIG ----------------
TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"  # <-- PUT YOUR BOT TOKEN HERE (keep it secret!)
BOT_DISPLAY_NAME = "Maya"
# ------------------------------------------------

# ANSI colours (termux-safe)
C_RESET = "\033[0m"
C_DIR = "\033[94m"      # blue
C_SERVER = "\033[96m"   # cyan
C_CHANNEL = "\033[92m"  # green
C_USER = "\033[93m"     # yellow
C_YOU = "\033[95m"      # magenta
C_SYS = "\033[90m"      # grey

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.dm_messages = True
intents.members = False  # on big servers may not be needed

client = discord.Client(intents=intents)

# pseudo-filesystem state
# path is list; root is []
# Example paths:
# []                              -> root
# ["discord"]                     -> inside discord (shows dm, servers)
# ["discord","dm"]                -> DM area: will use target_user_id var
# ["discord","servers"]           -> list servers
# ["discord","servers", guild_id] -> inside server (shows channels)
# ["discord","servers", guild_id, "channels", channel_id] -> inside a channel (chat mode targets this)
path = ["discord"]

# Current channel or DM target
current_guild = None   # discord.Guild object or None
current_channel = None # discord.TextChannel or None
dm_target_user_id = None  # optional user id for dm mode if you cd into dm/<id>

# Lock for printing to avoid interleaving
print_lock = threading.Lock()

def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)
        sys.stdout.flush()

def format_server_line(guild):
    return f"{C_SERVER}{guild.id}{C_RESET} [{guild.name}]"

def format_channel_line(ch):
    return f"{C_CHANNEL}{ch.id}{C_RESET} [{ch.name}]"

def prompt():
    # Build breadcrumb prompt like: [discord/servers/My Server/general]$
    comps = []
    if len(path) == 0:
        comps = ["root"]
    else:
        comps = path.copy()
    # prettify guild and channel names if available
    display = []
    i = 0
    while i < len(comps):
        p = comps[i]
        if p == "servers":
            display.append("servers")
            i += 1
            # if next is guild id and we have object, show name
            if i < len(comps):
                gid = comps[i]
                try:
                    gid_int = int(gid)
                    g = discord.utils.get(client.guilds, id=gid_int)
                    if g:
                        display.append(f"{g.name}")
                    else:
                        display.append(str(gid))
                except Exception:
                    display.append(str(gid))
                i += 1
        elif p == "channels":
            display.append("channels")
            i += 1
            if i < len(comps):
                cid = comps[i]
                try:
                    cid_int = int(cid)
                    ch = client.get_channel(cid_int)
                    if ch:
                        display.append(f"#{ch.name}")
                    else:
                        display.append(str(cid))
                except Exception:
                    display.append(str(cid))
                i += 1
        else:
            display.append(p)
            i += 1

    return f"[{'/'.join(display)}]$ "

# ---------- Command handlers ----------

def cmd_help():
    safe_print(C_SYS + "Available commands:" + C_RESET)
    safe_print("  ls                     - list items in current directory")
    safe_print("  cd <name|id|..>        - change directory (use server id or channel id)")
    safe_print("  pwd                    - show current path")
    safe_print("  clear                  - clear the terminal")
    safe_print("  chat                   - enter chat mode (type lines to send, '/exit' to leave)")
    safe_print("  send <message>         - send a message quickly")
    safe_print("  whoami                 - show bot identity")
    safe_print("  reconnect              - reconnect the bot")
    safe_print("  help                   - show this help")
    safe_print("  exit                   - quit the CLI")
    safe_print("")
    safe_print("Path structure examples:")
    safe_print("  discord/")
    safe_print("    dm/                -> private DM area")
    safe_print("    servers/           -> list your servers")
    safe_print("    servers/<id>/      -> channels of server id")
    safe_print("    servers/<id>/channels/<channel_id> -> open that text channel")

def cmd_pwd():
    safe_print("/" + "/".join(path))

def cmd_clear():
    os.system("clear")

def cmd_whoami():
    me = client.user
    safe_print(f"{C_SYS}Bot display: {C_RESET}{C_USER}{BOT_DISPLAY_NAME}{C_RESET} {C_SYS}(username: {me}, id: {me.id}){C_RESET}")

def cmd_list():
    # ls implementation depending on path
    if path == ["discord"]:
        safe_print(C_DIR + "dm/" + C_RESET)
        safe_print(C_DIR + "servers/" + C_RESET)
        return
    if path == ["discord","dm"]:
        safe_print(C_DIR + "dm/")
        safe_print(C_SYS + "Use 'chat' to DM a user. To target a specific user id: cd dm/<user_id>" + C_RESET)
        return
    if path == ["discord","servers"]:
        if not client.guilds:
            safe_print(C_SYS + "No servers found or bot not in any guilds." + C_RESET)
            return
        for g in client.guilds:
            safe_print(f"{C_SERVER}{g.id}{C_RESET} [{g.name}]")
        return
    # server specific
    if len(path) >= 3 and path[1] == "servers":
        # path like ["discord","servers", guild_id] or deeper
        try:
            guild_id = int(path[2])
            guild = discord.utils.get(client.guilds, id=guild_id)
            if guild is None:
                safe_print(C_SYS + "Guild not found or bot not a member." + C_RESET)
                return
            # if at server root
            if len(path) == 3:
                safe_print(C_SYS + f"Server: {guild.name} (id: {guild.id})" + C_RESET)
                safe_print(C_DIR + "channels/" + C_RESET)
                return
            # if in channels
            if len(path) >= 4 and path[3] == "channels":
                # list text channels
                text_ch = [c for c in guild.channels if isinstance(c, discord.TextChannel)]
                if not text_ch:
                    safe_print(C_SYS + "No text channels in this server." + C_RESET)
                    return
                for ch in text_ch:
                    safe_print(f"{C_CHANNEL}{ch.id}{C_RESET} [{ch.name}]")
                return
        except Exception:
            safe_print(C_SYS + "Invalid server id." + C_RESET)
            return

    safe_print(C_SYS + "Nothing to list here." + C_RESET)

def change_dir(target):
    global current_guild, current_channel, dm_target_user_id
    if target in ["..", "back"]:
        if len(path) > 1:
            path.pop()
        return
    # cd to root discord
    if target == "discord":
        path.clear()
        path.append("discord")
        current_guild = None
        current_channel = None
        dm_target_user_id = None
        return
    # inside discord
    if path == ["discord"]:
        if target == "dm":
            path.clear()
            path.extend(["discord","dm"])
            current_guild = None
            current_channel = None
            return
        if target == "servers":
            path.clear()
            path.extend(["discord","servers"])
            current_guild = None
            current_channel = None
            return
        # try if user typed cd <id> to jump directly to server
        try:
            maybe = int(target)
            # check if that guild exists
            g = discord.utils.get(client.guilds, id=maybe)
            if g:
                path.clear()
                path.extend(["discord","servers", str(maybe)])
                current_guild = g
                current_channel = None
                return
        except Exception:
            pass
        safe_print(C_SYS + "Unknown target. Try 'ls'." + C_RESET)
        return
    # inside servers listing
    if path[:2] == ["discord","servers"]:
        # if currently at servers/ (list of all), and target is id or name
        if len(path) == 2:
            # allow name match
            for g in client.guilds:
                if str(g.id) == target or g.name.lower() == target.lower():
                    path.clear()
                    path.extend(["discord","servers", str(g.id)])
                    current_guild = g
                    current_channel = None
                    return
            safe_print(C_SYS + "Server not found. Use server id or exact name." + C_RESET)
            return
        # if at server root and target is channels
        if len(path) == 3:
            if target == "channels":
                path.append("channels")
                current_channel = None
                return
            # maybe cd channel id directly
            try:
                maybe = int(target)
                gid = int(path[2])
                g = discord.utils.get(client.guilds, id=gid)
                if g:
                    ch = g.get_channel(maybe) or discord.utils.get(g.channels, id=maybe)
                    if ch and isinstance(ch, discord.TextChannel):
                        path.clear()
                        path.extend(["discord","servers", str(gid), "channels", str(ch.id)])
                        current_guild = g
                        current_channel = ch
                        return
            except Exception:
                pass
            safe_print(C_SYS + "Unknown target. Try 'ls' or 'cd channels'." + C_RESET)
            return
        # if in channels listing and target is channel id or name
        if len(path) >= 4 and path[3] == "channels":
            guild_id = int(path[2])
            guild = discord.utils.get(client.guilds, id=guild_id)
            if not guild:
                safe_print(C_SYS + "Guild missing." + C_RESET)
                return
            # match by id or name
            for ch in guild.channels:
                if not isinstance(ch, discord.TextChannel):
                    continue
                if str(ch.id) == target or ch.name.lower() == target.lower():
                    path.clear()
                    path.extend(["discord","servers", str(guild_id), "channels", str(ch.id)])
                    current_guild = guild
                    current_channel = ch
                    return
            safe_print(C_SYS + "Channel not found. Use channel id or exact name." + C_RESET)
            return

    # inside dm folder: allow cd <user_id> to target user for immediate chat mode
    if path == ["discord","dm"]:
        try:
            uid = int(target)
            dm_target_user_id = uid
            path.clear()
            path.extend(["discord","dm", str(uid)])
            current_guild = None
            current_channel = None
            return
        except Exception:
            safe_print(C_SYS + "Invalid user id." + C_RESET)
            return

    safe_print(C_SYS + "cd: can't go there" + C_RESET)

def resolve_current_target():
    """Return (target_type, object) where target_type in ('dm_user','channel')"""
    if len(path) >= 4 and path[:4] == ["discord","servers", path[2], "channels"]:
        # channel mode
        try:
            cid = int(path[4])
            ch = client.get_channel(cid)
            return ("channel", ch)
        except Exception:
            return (None, None)
    if len(path) >= 3 and path[:2] == ["discord","dm"]:
        try:
            uid = int(path[2])
            u = client.get_user(uid)
            return ("dm_user", u)
        except Exception:
            return (None, None)
    return (None, None)

def send_text(text):
    """Schedules send to the current target (channel or dm)"""
    ttype, obj = resolve_current_target()
    if ttype == "channel":
        if obj is None:
            safe_print(C_SYS + "Channel object not available (maybe bot lacks access or cached). Try reconnect or use 'send <msg>' with full channel id." + C_RESET)
            return
        fut = asyncio.run_coroutine_threadsafe(obj.send(text), client.loop)
        try:
            fut.result(10)
            safe_print(f"{C_YOU}[You]{C_RESET} {text}")
        except Exception as e:
            safe_print(C_SYS + f"Failed to send: {e}" + C_RESET)
    elif ttype == "dm_user":
        if obj is None:
            # try fetch
            try:
                uid = int(path[2])
                fut = asyncio.run_coroutine_threadsafe(client.fetch_user(uid), client.loop)
                u = fut.result(10)
                fut2 = asyncio.run_coroutine_threadsafe(u.send(text), client.loop)
                fut2.result(10)
                safe_print(f"{C_YOU}[You]{C_RESET} {text}")
            except Exception as e:
                safe_print(C_SYS + f"Failed to DM: {e}" + C_RESET)
        else:
            fut = asyncio.run_coroutine_threadsafe(obj.send(text), client.loop)
            try:
                fut.result(10)
                safe_print(f"{C_YOU}[You]{C_RESET} {text}")
            except Exception as e:
                safe_print(C_SYS + f"Failed to DM: {e}" + C_RESET)
    else:
        safe_print(C_SYS + "No target selected. Use 'cd' to pick a channel or cd dm/<user_id>." + C_RESET)

def cmd_send_rest(args):
    if not args:
        safe_print(C_SYS + "Usage: send <message>" + C_RESET)
        return
    text = " ".join(args)
    send_text(text)

def chat_mode():
    safe_print(C_SYS + "Entering chat mode. Type '/exit' to leave chat mode." + C_RESET)
    try:
        while True:
            line = input()
            if line.strip() == "/exit":
                safe_print(C_SYS + "Exiting chat mode." + C_RESET)
                break
            if not line:
                continue
            send_text(line)
    except KeyboardInterrupt:
        safe_print(C_SYS + "\nChat mode interrupted." + C_RESET)

def reconnect():
    safe_print(C_SYS + "Reconnecting..." + C_RESET)
    # Best-effort: restart the client by scheduling a close and start
    try:
        asyncio.run_coroutine_threadsafe(client.close(), client.loop).result(10)
    except Exception:
        pass
    # Start client again in background thread
    t = threading.Thread(target=lambda: client.run(TOKEN), daemon=True)
    t.start()
    safe_print(C_SYS + "Reconnect attempted." + C_RESET)

# ---------- Input thread (started after on_ready) ----------

def cli_loop_thread():
    # Main command loop using synchronous input, but scheduling discord coroutines via client's loop
    while True:
        try:
            p = prompt()
            cmdline = input(p).strip()
        except (EOFError, KeyboardInterrupt):
            safe_print("")
            safe_print(C_SYS + "Exiting CLI..." + C_RESET)
            try:
                asyncio.run_coroutine_threadsafe(client.close(), client.loop)
            except Exception:
                pass
            os._exit(0)

        if not cmdline:
            continue
        parts = cmdline.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "help":
            cmd_help()
        elif cmd == "ls":
            cmd_list()
        elif cmd == "pwd":
            cmd_pwd()
        elif cmd == "clear":
            cmd_clear()
        elif cmd == "whoami":
            cmd_whoami()
        elif cmd == "cd":
            if not args:
                safe_print(C_SYS + "Usage: cd <target>" + C_RESET)
            else:
                change_dir(args[0])
        elif cmd == "chat":
            chat_mode()
        elif cmd == "send":
            cmd_send_rest(args)
        elif cmd == "reconnect":
            reconnect()
        elif cmd == "exit" or cmd == "quit":
            safe_print(C_SYS + "Shutting down..." + C_RESET)
            try:
                asyncio.run_coroutine_threadsafe(client.close(), client.loop).result(5)
            except Exception:
                pass
            os._exit(0)
        else:
            safe_print(C_SYS + f"Unknown command: {cmd}. Type 'help'." + C_RESET)

# ---------- Discord event handlers ----------

@client.event
async def on_ready():
    safe_print(C_SYS + f"Logged in as {client.user} ({BOT_DISPLAY_NAME})" + C_RESET)
    safe_print(C_SYS + "Starting CLI. Type 'help' for commands." + C_RESET)
    # start CLI thread
    t = threading.Thread(target=cli_loop_thread, daemon=True)
    t.start()

@client.event
async def on_message(message):
    # ignore own messages
    if message.author.id == client.user.id:
        return

    # Determine where this message came from and print a formatted line
    ts = time.strftime("%H:%M", time.localtime(message.created_at.timestamp()))
    author = f"{C_USER}{message.author.display_name}{C_RESET}"
    content = message.content

    # DM
    if isinstance(message.channel, discord.DMChannel):
        safe_print(f"[{ts}] {author}: {content}")
        return

    # Guild channel
    ch = message.channel
    g = getattr(ch, "guild", None)
    if g:
        # If user currently in this channel, just print normally (context is obvious)
        try:
            current = "/".join(path)
        except Exception:
            current = ""
        # include guild and channel info for clarity
        safe_print(f"[{ts}] {C_SERVER}{g.name}{C_RESET}/{C_CHANNEL}{ch.name}{C_RESET} {author}: {content}")

# ---------- Start the bot ----------

def sanity_check_token():
    if not TOKEN or TOKEN.startswith("PASTE") or TOKEN.strip() == "":
        safe_print(C_SYS + "ERROR: You must set TOKEN in the script before running. Exiting." + C_RESET)
        sys.exit(1)

def main():
    sanity_check_token()
    try:
        client.run(TOKEN)
    except Exception as e:
        safe_print(C_SYS + f"Client terminated: {e}" + C_RESET)

if __name__ == "__main__":
    main()
