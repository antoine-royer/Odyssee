from math import ceil
from libs.players import *
from libs.travel import *


# --- Fonctions de sauvegarde --- #


# export_save : enregistre les joueurs dans 'save.txt'
def export_save(data_player, data_kick, guild_id):
    print("Partie enregistrée")
    save = [[data_player[player_id].export() for player_id in data_player], data_kick, guild_id]
    with open("save.txt", "w") as file:
        file.write(str(save))


# load_save : charge les joueurs depuis 'save.txt'
def load_save():
    print("Chargment de la partie")
    try:
        with open("save.txt", "r") as file:
            data_player, data_kick, guild_id = eval(file.read())
        print("... partie chargée")
        return {player[0]: Player(*player) for player in data_player}, data_kick, guild_id
    
    except:
        print("... aucune partie trouvée\n... création d'une nouvelle partie")
        with open("save.txt", "w") as file:
            file.write("[[], [], 0]")
        return {}, [], 0


# --- Fonctions diverses --- #


# get_user : renvoie le nom et l'id
def get_user(ctx):
    if ctx.author.nick:
        return ctx.author.nick, ctx.author.id
    else:
        return ctx.author.name, ctx.author.id


async def send_error(ctx, msg):
    await ctx.send(f"*Erreur : {msg}.*")


# get_avg_level : renvoie le niveau moyen des joueurs
def get_avg_level(data_player):
    level, total = 0, 0
    for player in data_player.values():
        if player.id > 0:
            level += player.get_level()
            total += 1

    return ceil(level / total)


# --- Fonctions de combats --- #

def phase_1(player, target):
    