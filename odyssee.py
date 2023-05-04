# --------------------------------------------------
# Odyssée (version 5.4.3)
# by Sha-chan~
# last modification on April 30, 2023
#
# code provided with licence:
# GNU General Public Licence v3.0
# --------------------------------------------------

import asyncio
import discord
from discord.ext import commands
import json
import os

from libs.commands import OdysseeCommands, AdminCommands, load_save


if not "saves" in os.listdir():
    os.mkdir("saves")

with open("config.json", "r") as file:
    config = json.load(file)

intents = discord.Intents.default()
odyssee = commands.Bot(command_prefix=commands.when_mentioned_or(config["PREFIX"]), strip_after_prefix=True, intents=discord.Intents.all())
save = load_save()


async def setup():
    for cmnd_module in (OdysseeCommands, AdminCommands):
        await odyssee.add_cog(cmnd_module(config, save, odyssee))


@odyssee.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching, name=config["PREFIX"] + "aide")
    await odyssee.change_presence(activity=activity)
    print("Connecté")


asyncio.run(setup())
odyssee.run(config["TOKEN"])
