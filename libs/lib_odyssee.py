from math import ceil
from random import randint
import requests
from bs4 import BeautifulSoup
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


def get_categories():
    cat = requests.get("https://www.nomsdefantasy.com/").text
    return ", ".join([cat.get("id") for cat in BeautifulSoup(cat, features="html5lib").find_all("input", {"name": "type"})])


# --- Fonctions de combats --- #

def phase_1(player, target):
    player_point, target_point = 0, 0
    while player_point == target_point:
        player_point = player.stat[0] + player.stat[3] + randint(1, 10)
        target_point = target.stat[0] + target.stat[3] + randint(1, 10)

    if player_point > target_point:
        return (player, target), 1
    else:
        return (target, player), 0


def phase_2(fighter):
    return fighter.capacity_roll(2) >= 0.5


def phase_3(fighters, attacker, defender):
    level = fighters[attacker].get_level()

    damage = fighters[attacker].stat[1] + randint(-10 * level, 10 * level)
    if fighters[attacker].stat[8] > fighters[attacker].max_weight:
        damage -= (fighters[attacker].stat[8] - fighters[attacker].max_weight)

    damage -= fighters[defender].stat[4]
    if damage < 0: damage = 0

    fighters[defender].stat[5] -= damage

    return damage
    