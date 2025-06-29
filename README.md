[Vid Demo](https://youtu.be/7y1e3CUuZHg)
[Download directly from dist folder](https://github.com/arhiv2ch/MGO-KM/tree/main/dist)

Real-time moderation tool for Metal Gear Online (MGSV - MGO) — designed to give lobby hosts basic control: see who’s in, kick unwanted players, and automatically block known offenders with a simple blacklist system.
It runs as an external .exe, requires no injection, no patching, and doesn’t interfere with game logic or other players.

What It Does:
See the Steam IDs and nicknames of everyone currently in your lobby. The tool reads directly from MGO's memory to find active player slots and fetches each Steam ID.
For each Steam ID, the tool performs an HTTP request to the player’s public Steam profile and parses their current display name. This happens on demand and is cached to avoid spamming Steam servers.
As the host, you can select any player in the list and remove them from the lobby. The tool writes directly to a known in-memory flag (KICK_OFFSET) for that player’s entity.
You can maintain a blacklist.json file of unwanted Steam IDs. As soon as any of those players join your lobby, the tool will kick them automatically — no input needed.
Built-in editor lets you view, format, and update your blacklist, including online nickname lookups for context.

///

Steam ID detection:
The tool attaches to mgsvmgo.exe and follows a known base pointer (PLAYER_LIST_BASE) to the in-memory structure holding all player slot data. Each slot contains a valid pointer to an entity, and from there the Steam ID is read via a fixed offset (STEAMID_OFFSET).
Kicking a player:
Each player structure has a field (KICK_OFFSET) which can be toggled (written to) to trigger a removal from lobby. This is handled cleanly and only affects the host's session.
Nickname parsing:
The tool makes a simple HTTP request to https://steamcommunity.com/profiles/<steamid> and scrapes the nickname from the HTML. It avoids repeated requests by caching names for 30 seconds.

Works with Windows 10 / 11 & Python 3.10+ or a compiled .exe build

Stack:
tkinter
pymem
requests
pyperclip
json 

///

This is not a cheat, and does not hook or tamper with the game engine. 
It’s a host-side tool for self-moderation — useful when playing with randoms, hosting casual matches, or dealing with cheaters/spam players in public lobbies.
No remote code, no unfair gameplay advantage, no server manipulation. The pointers are quite stable, I expect that they will work for any user.

This tool is open-source and safe to use, but since it's compiled as a standalone .exe and includes memory access (it reads memory from mgsvmgo.exe) as well as simple HTTP requests (to fetch nicknames from Steam), it may trigger false positives on some antivirus scanners.
[VirusTotal scan here](https://www.virustotal.com/gui/file/2ca2f2e679541034f6a8c97e045e56b16f337681945d222c2df23ee1fc2c506f/detection)
