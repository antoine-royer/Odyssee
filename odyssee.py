# --------------------------------------------------
# Odyssée (version 5.4.0)
# by Sha-chan~
# last modification on April 25, 2022
#
# code provided with licence :
# GNU General Public Licence v3.0
# --------------------------------------------------

import discord
from discord.ext import commands
import json
import os

from libs.commands import OdysseeCommands, AdminCommands, load_save

if not "saves" in os.listdir():
    os.mkdir("saves")

with open("config.json", "r") as file:
    config = json.load(file)

odyssee = commands.Bot(command_prefix=commands.when_mentioned_or(config["PREFIX"]), strip_after_prefix=True)

save = load_save()

for cmnd_module in (OdysseeCommands, AdminCommands):
    odyssee.add_cog(cmnd_module(config, save, odyssee))


@odyssee.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching, name=config["PREFIX"] + "aide")
    await odyssee.change_presence(activity=activity)
    print("Connecté")

odyssee.run(config["TOKEN"])
