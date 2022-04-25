from bs4 import BeautifulSoup
from math import ceil
import json
import os
from random import randint
import requests

from libs.players import *
from libs.travel import *
from libs.states import *
from libs.wikiphyto import wikiphyto_api


# --- Fonctions de sauvegarde --- #


# export_save : enregistre les joueurs dans 'save.txt'
def export_save(data_player, data_kick, guild_id, save_name=""):
    if save_name: save_name = "_" + save_name
    print(" - Partie enregistrée -")
    
    with open(f"saves/save{save_name}.json", "w") as file:
        file.write(json.dumps(
            {
                "players": [data_player[player_id].export() for player_id in data_player], 
                "kicks": data_kick, 
                "guild_id": guild_id
            }, indent=4))


# load_save : charge les joueurs depuis 'save.txt'
def load_save(save_name=""):
    if save_name: save_name = "_" + save_name
    print(" - Chargement de la partie - ")
    
    try:
        with open(f"saves/save{save_name}.json", "r") as file:
            data = json.loads(file.read())
            data_player, data_kick, guild_id = data["players"], data["kicks"], data["guild_id"]

        data_player = {player[0]: Player(*player) for player in data_player}
        print("... partie chargée")
        return data_player, data_kick, guild_id
    
    except:
        print("... aucune partie trouvée\n... création d'une nouvelle partie")
        with open("saves/save.json", "w") as file:
            file.write("""{
    "players": [],
    "kicks": [],
    "guild_id": 0
}""")

        return {}, [], 0


# search_save : recherche une save et la charge si elle existe
def search_save(save_name):
    save_name = f"save_{save_name}.json"
    print(" - Recherche d'une partie -")
    if save_name in os.listdir("saves"):
        print("... partie trouvée")
        with open(f"saves/{save_name}", "r") as file:
            data = json.loads(file.read())
            data_player, data_kick, guild_id = data["players"], data["kicks"], data["guild_id"]

        # data_player = {player[0]: Player(*player) for player in data_player}
        print("... partie chargée")
        return data_player, data_kick, guild_id

    else:
        print("... partie introuvable")
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
    return (fighter.capacity_roll(2) >= 2) or (fighter.capacity_roll(1) == 3)


def phase_3(fighters, attacker, defender):
    level = fighters[attacker].get_level()

    damage = fighters[attacker].stat[1] + randint(-5 * level, 10 * level)
    if fighters[attacker].stat[9] > fighters[attacker].max_weight:
        damage -= (fighters[attacker].stat[9] - fighters[attacker].max_weight)
        if fighters[attacker].state == 3: damage -= fighters[attacker].get_level() * 5

    damage -= fighters[defender].stat[5]
    if damage < 0: damage = 0

    fighters[defender].stat[6] -= damage

    return damage


def weapon_select(player):
    # Si player n'est pas en état de se battre
    if player.state in (2, 4):
        if player.state == 4: player.state = 0
        return False, Object("", "", [0 for i in range(9)], -1, -1)

    # On cherche une arme à distance
    weapon = player.select_object_by_type(4)
    if weapon != -1:
        # Si il en existe une, on regarde les projectiles
        index = player.select_object_by_type(5)
        if index != -1:
            player.inventory[index].quantity -= 1
            if player.inventory[index].quantity <= 0: player.inventory.pop(index)

            return True, player.inventory[weapon]

    # On cherche une arme de mêlée
    weapon = player.select_object_by_type(3)
    if weapon == -1:
        return True, Object("ses mains", "ses mains", [int(i == 8) for i in range(9)], -1, -1)    
    else:
        return True, player.inventory[weapon]


def weapon_check(player, target, weapon):
    index, weapon = player.have(weapon)
    # si le joueur n'a pas l'arme demandée
    if index == -1: return None, 1

    # si c'est une arme connue
    elif weapon.object_type in (3, 4):

        # arme de mêlée => même lieu
        if weapon.object_type == 3 and target.place != player.place:
            return None, 2

        # arme à distance => nécessite un projectile
        if weapon.object_type == 4:
            arrow_index = player.select_object_by_type(5)
            if arrow_index == -1:
                return None, 3
            else:
                player.inventory[arrow_index].quantity -= 1
                if player.inventory[arrow_index].quantity <= 0: player.inventory.pop(arrow_index)

    # s'il s'agit d'un objet quelconque
    else:
        weapon = player.inventory[index]

    return weapon, 0