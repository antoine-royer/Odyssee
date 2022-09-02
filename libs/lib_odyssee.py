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


def phase_2(fighter, defender):
    return (fighter.stat[2] - defender.stat[2] > 20 * defender.get_level()) or (fighter.capacity_roll(2) >= 2) or (fighter.capacity_roll(1) == 3)


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


async def fight_main(player, target, arme, data_player, ctx):
    # Vérification de l'arme du joueur
    if arme:
        player_weapon, check = weapon_check(player, target, arme)
        if check == 1: await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{arme}'"); return
        elif check == 2: await send_error(ctx, f"__{player.name}__ et __{target.name}__ ne sont pas au même endroit"); return
        elif check == 3: await send_error(ctx, f"__{player.name} n'a pas de projectile pour tirer"); return

    # Si aucune arme n'a été précisée
    elif target.place != player.place:
            await send_error(ctx, f"__{player.name}__ et __{target.name}__ ne sont pas au même endroit")
            return
    else:
        player_weapon = Object("ses mains", "ses mains", [int(i == 8) for i in range(9)], -1, -1)

    # Arme de l'adversaire
    target_can_fight, target_weapon = weapon_select(target)
    if target_weapon.object_type != 4 and target.place != player.place: target_can_fight = False
    if player.state == 6: target_can_fight = False

    # Affichage des statistiques et des modificateurs
    capacities = list(get_capacities()[:6])
    capacities.insert(0, "Capacités")

    max_lgth = len(capacities[0])

    player_capacities = [player.name]
    player_max_lgth = len(player.name)

    target_capacities = [target.name]
    target_max_lgth = len(target.name)

    pml, tml = 0, 0
    for i in range(len(capacities)):
        pml = max(pml, len(str(player.stat[i])))
        tml = max(tml, len(str(target.stat[i])))

    for index in range(len(capacities)):
        max_lgth = max(len(capacities[index]), max_lgth)

        player_capacities.append(f"{player.stat[index]}{' ' * (pml - len(str(player.stat[index])))} [{('', '+')[player_weapon.stat[index] >= 0]}{player_weapon.stat[index]}]")
        player_max_lgth = max(len(player_capacities[-1]), player_max_lgth)

        target_capacities.append(f"{target.stat[index]}{' ' * (tml - len(str(target.stat[index])))} [{('', '+')[target_weapon.stat[index] >= 0]}{target_weapon.stat[index]}]")
        target_max_lgth = max(len(target_capacities[-1]), target_max_lgth)

    message = f"```\n"
    
    for index, name in enumerate(capacities):
        message += f"{name.capitalize() + ' ' * (max_lgth - len(name))} | {player_capacities[index] + ' ' * (player_max_lgth - len(player_capacities[index]))} | {target_capacities[index] + ' ' * (target_max_lgth - len(target_capacities[index]))}\n"

    message += "```\n"

    player.stat_add(player_weapon.stat)
    target.stat_add(target_weapon.stat)

    # Qui commence
    fighters, target_index = phase_1(player, target)

    for attacker in range(2):
        defender = (attacker + 1) % 2

        turn = True
        if attacker == target_index and not target_can_fight:
            message += f"__{fighters[target_index].name}__ ne peut pas se battre.\n"
            if player.state == 6: message += f"(car __{player.name}__ est invisible)"
            turn = False

        end = False
        if turn:
            message += f"__{fighters[attacker].name}__ attaque"
            if attacker == target_index: message += f" avec {target_weapon.name}"
            else: message += f" avec {player_weapon.name}"

            if phase_2(fighters[attacker], fighters[defender]):
                message += " et touche sa cible.\n"

                damage = phase_3(fighters, attacker, defender)
                if damage:
                    if fighters[defender].state != 5 and fighters[defender].stat[6] < fighters[defender].get_max_health(): fighters[defender].state = 3
                    message += f"__{fighters[defender].name}__ subit {damage} point{('', 's')[damage > 1]} de dégâts.\n"
                else:
                    message += f"La défense de __{fighters[defender].name}__ encaisse les dégats.\n"

                if not fighters[defender].isalive():
                    loot = f"__{fighters[defender].name}__ est mort, __{fighters[attacker].name}__ fouille le cadavre et trouve :\n"
                    
                    if fighters[defender].stat[8]:
                        loot += f" ❖ {fighters[defender].stat[8]} Drachme{('', 's')[fighters[defender].stat[8] > 1]}\n"
                        fighters[attacker].stat[8] += fighters[defender].stat[8]
                    
                    for obj in fighters[defender].inventory:
                        check = fighters[attacker].object_add(*fighters[attacker].have(obj.name), obj.quantity, obj.name)
                        if check: loot += f" ❖ {obj.name}{('', f' ({obj.quantity})')[obj.quantity > 1]}\n"

                    data_player.pop(fighters[defender].id)

                    message += loot
                    end = True
            else:
                message += f" et manque sa cible.\n"

        if end: break

    player.stat_sub(player_weapon.stat)
    target.stat_sub(target_weapon.stat)

    return message


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