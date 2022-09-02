# Statistiques : Courage (0), Force (1), Habileté (2), Rapidité (3), Intelligence (4), Défense (5), Vie (6), Mana (7), Argent (8), Poids porté (9), Couleur (10)

from random import randint
from libs.objects import *
from libs.powers import *
from libs.states import *


# --- Constructeur du joueur --- #


# stat_gen : générateur de statistiques
def stat_gen(factor, level=1, enemy=False):
    if level < 1: level = 1
    color = randint(0, 16777215)
    
    stat = [int(factor[i] * randint(20 * (level - 1), 20 * level)) for i in range(5)]
    stat.append(0)
    
    if enemy:
        stat += [randint(25, 100 + 50 * (level - 1)), 5, randint(5 * level, 10 * (level + 1)), 0, color]
    else:
        stat += [100, 5, 30, 0, color]
    return stat


# roll_die : simule un lancer de dé
def roll_die(faces=20, nb=1):
    return randint(nb, nb * faces)


def get_capacities():
    return ("courage", "force", "habileté", "rapidité", "intelligence", "défense", "vie", "mana", "argent")

# Player : contient les infos des joueurs (PnJ compris)
class Player:
    def __init__(self, identifier, name, species, avatar=None, stat=None, place="< inconnu >", stat_modifier=None, inventory=None, note=None, power=None, state=0, abilities=None):
        self.id = identifier
        self.name = name
        self.species = species
        self.place = place
        self.state = state
        self.avatar = avatar

        if stat: self.stat = stat
        else: self.stat = stat_gen(get_species(species)[2:])
        self.max_weight = 5 * (self.stat[1] + 1)

        if stat_modifier: self.stat_modifier = stat_modifier
        else: self.stat_modifier = [0 for _ in range(8)]
        
        if inventory: self.inventory = [Object(*i) for i in inventory]
        else: self.inventory = list()

        if note: self.note = note
        else: self.note = [[0, ""]]

        if power: self.power = [Power(*i) for i in power]
        else:
            default_power = get_default_power(species)
            if default_power: self.power = [default_power]
            else: self.power = []

        if abilities: self.abilities = abilities[:]
        else:
            self.abilities = []

    def export(self):
        if self.state == 3 and self.stat[6] >= self.get_max_health(): self.state = 0
        return [self.id, self.name, self.species, self.avatar, self.stat, self.place, self.stat_modifier, [i.export() for i in self.inventory], self.note, [i.export() for i in self.power], self.state, self.abilities]

    async def get_avatar(self, guild):
        player = await guild.fetch_member(self.id)
        self.avatar = str(player.avatar_url)

    def isalive(self):
        return self.stat[6] > 0

    def get_max_weight(self):
        return 2 * self.stat[1]
        
    def isoverweight(self):
        max_weight = self.get_max_weight()
        if self.stat[9] > max_weight: return self.stat[9] - max_weight
        else: return 0

    def get_max_health(self):
        return (100 + (self.get_level() - 1) * 25)

    def get_level(self):
        return (sum(self.stat[:5]) // 100) + 1

    def get_state(self):
        return get_state_by_id(self.state)

    def capacity_roll(self, capacity_index):
        overweight = self.isoverweight()
        if self.state == 3 or overweight: malus = (self.get_max_health() - self.stat[6]) // 10 + (overweight // 10)
        else: malus = 0
        
        point = (randint(1, 20) + self.stat[capacity_index] - malus) / (40 * self.get_level())

        if point >= 0.75:
            return 3 # succès critique
        elif point >= 0.5:
            return 2 # succès
        elif point >= 0.25:
            return 1 # échec
        else: return 0 # échec critique

    def get_stat(self):
        return [self.name, self.species, self.get_level()] + self.stat + [self.place, [(i.name, i.quantity) for i in self.inventory], self.note, self.avatar, [i.name for i in self.power], self.get_state(), [(i[0], i[1]) for i in self.abilities]]

    # Du courage à la mana (incluse)
    def stat_add(self, stat_to_add):
        for i in range(8): self.capacity_modify(i, stat_to_add[i])

    def stat_sub(self, stat_to_sub):
        for i in range(8): self.capacity_modify(i, -stat_to_sub[i])

    def have(self, object_name): # Renvoie : (index, Object), Object.type = -1 si l'objet est inconnu ; index = -1 si l'objet n'est pas possédé
        object_name = get_official_name(object_name, True)
        for index, obj in enumerate(self.inventory):
            if object_name == obj.official_name:
                return index, obj

        return -1, get_object(object_name)

    def object_add(self, index, obj, nb, object_name):
        # Objet stockable en plusieurs exemplaire
        if obj.object_type in (1, 5, 8):
            self.stat[9] += nb * obj.stat[9]

            if index + 1: # Objet déjà possédé
                self.inventory[index].quantity += nb
            else: # Pas encore possédé
                obj.name = object_name
                obj.quantity = nb
                self.inventory.append(obj)
            return 1

        elif index == -1: # Si stockable en un seul exemplaire et que l'objet n'est pas dans l'inventaire
            self.stat[9] += obj.stat[9]
            obj.name = object_name
            obj.quantity = 1
            if obj.object_type in (0, 2, 7, 8): self.stat_add(obj.stat)
            if obj.object_type != 2:
                self.inventory.append(obj)
                return 2
            else:
                return 3
        else:
            return 0

    def object_del(self, index, obj, nb, force_mode=False):
        # Objet non possédé ou pas en assez grande quantité
        if index == -1 or (self.inventory[index].quantity < nb and not force_mode):
            return 0

        else:
            if nb > self.inventory[index].quantity: nb = self.inventory[index].quantity
            self.stat[9] -= nb * obj.stat[9]
            self.inventory[index].quantity -= nb
            if self.inventory[index].quantity <= 0: self.inventory.pop(index)
            if obj.object_type in (0, 7, 8): self.stat_sub(obj.stat)
            return 1

    def object_use(self, object_name, nb):
        index, obj = self.have(object_name)

        # Objet non possédé ou pas en assez grande quantité
        if index == -1 or self.inventory[index].quantity < nb:
            return 0

        if obj.object_type in (1, 5, 8):
            self.stat[9] -= nb * obj.stat[9]
            for _ in range(nb):
                self.stat_add(obj.stat)
            self.inventory[index].quantity -= nb
            if self.inventory[index].quantity <= 0: self.inventory.pop(index)
            return 1
        else:
            return 2

    def capacity_modify(self, capacity_index, amount):
        self.stat[capacity_index] += amount
        if self.stat[capacity_index] < 0: self.stat[capacity_index] = 0

    def add_note(self, note):
        if len(self.note) == 1 and not self.note[0][0]:
            self.note[0] = [1, note]
        else:
            self.note.append([len(self.note) + 1, note])

    def del_note(self, note_index):
        if len(self.note) >= note_index:                
            for index in range(note_index - 1, len(self.note)): self.note[index][0] -= 1

            content = self.note[note_index - 1][1]
            del(self.note[note_index - 1])

            if not self.note: self.note.append([0, ""])
            return content

    def power_add(self, power_name):
        power = get_power_by_name(power_name)
        
        # Pouvoir non enregistré
        if not power:
            return 0

        # Pouvoir déjà possédé ou trop de pouvoirs
        elif power.power_id in [i.power_id for i in self.power] or len(self.power) >= 3 + (self.stat[4] // 20):
            return 1
        
        # Succès
        else:
            self.power.append(power)
            return 2

    def power_sub(self, power_name):
        power = get_power_by_name(power_name)
        powers_id = [i.power_id for i in self.power]

        # Pouvoir non enregistré
        if not power:
            return 0

        # Pouvoir non possédé
        elif power.power_id not in powers_id:
            return 1

        # Succès
        else:
            self.power.pop(powers_id.index(power.power_id))
            return 2

    def in_shop(self):
        shop_name = get_shop_name()
        current_place = self.place.lower()

        for shop_id, shop in enumerate(shop_name):
            for name in shop:
                if name in current_place:
                    return shop_id
        return -1

    def select_object_by_type(self, *search_types):
        for index, obj in enumerate(self.inventory):
            if obj.object_type in search_types:
                return index
        return -1

    def add_abilities(self, ab_name, index, pts=1):
        if index == -1:
            self.abilities.append([ab_name, pts])
            return 1
        else:
            if self.abilities[index][1] + pts < 20: self.abilities[index][1] += pts
            return 2

    def sub_abilities(self, ab_name, index, pts=1):
        self.abilities[index][1] -= pts

        if self.abilities[index][1] <= 0:
            self.abilities.pop(index)
            return 1 # le joueur perd la compétence
        else:
            return 2 # le joueur perd un point

    def have_abilities(self, ab_name):
        ab_name = ab_name.lower()
        for index, ab in enumerate(self.abilities):
            if ab_name == ab[0].lower(): return index

        return -1

    def sleep(self):
        lvl = self.get_level()
        max_mana = lvl * 5

        self.stat_sub(self.stat_modifier)
        self.stat_modifier = [0 for _ in range(8)]
        
        # Régénération de la vie
        if self.stat[6] < self.get_max_health():
            if self.state == 0: self.state = 3
            self.stat[6] += 5 * lvl

        # Régénération de la mana
        if self.state != 3 and self.stat[7] < 5 + (lvl - 1):
            mana = 1 + (lvl // 2)
            for obj in self.inventory:
                mana += obj.stat[7]
            self.stat[7] += mana

        # Empoisonné
        if self.state == 1:
            self.stat[6] -= random(1, 12) * lvl

        # Inconscient, endormi
        if self.state in (2, 4):
            self.state = 0
        
        # Blessé
        if self.state == 3 and self.stat[6] >= self.get_max_health():
            self.state = 0

        # Transformé | Invisible
        if self.state in (5, 6):
            self.state = (3, 0)[self.stat[6] >= self.get_max_health()]






