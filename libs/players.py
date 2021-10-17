# Statistiques : Courage (0), Force (1), Habileté (2), Rapidité (3) Défense (4), Vie (5), Mana (6), Argent (7), Poids porté (8), Couleur (9)

from random import randint
from libs.shop import *
from libs.powers import *


# --- Constructeur du joueur --- #


# stat_gen : générateur de statistiques
def stat_gen(factor, level=1, enemy=False):
    if level < 1: level = 1
    color = randint(0, 16777215)
    
    stat = [int(factor[i] * randint(20*(level-1), 20*level)) for i in range(4)]
    stat.append(0)
    
    if enemy:
        stat += [randint(25, 50 * level), 0, randint(2, 10 * level), 0, color]
    else:
        stat += [100, 5, 15, 0, color]
    return stat


# roll_die : simule un lancer de dé
def roll_die(faces = 20, nb = 1):
    return randint(nb, nb * faces)


# Player : contient les infos des joueurs (PnJ compris)
class Player:
    def __init__(self, identifier, name, species, avatar=None, stat=None, place="< inconnu >", inventory=None, note=None, power=None):
        self.id = identifier
        self.name = name
        self.species = species
        self.place = place
        self.avatar = avatar

        if stat: self.stat = stat
        else: self.stat = stat_gen(get_species(species)[2:])
        self.max_weight = 5 * (self.stat[1] + 1)
        
        if inventory: self.inventory = [Object(*i) for i in inventory]
        else: self.inventory = list()

        if note: self.note = note
        else: self.note = [[0, ""]]

        if power: self.power = [Power(*i) for i in power]
        else:
            default_power = get_default_power(species)
            if default_power: self.power = [default_power]
            else: self.power = []

    def export(self):
        return self.id, self.name, self.species, self.avatar, self.stat, self.place, [i.export() for i in self.inventory], self.note, [i.export() for i in self.power]

    def isalive(self):
        return self.stat[5] > 0

    def get_level(self):
        return (sum(self.stat[:4]) // 80) + 1

    def capacity_roll(self, capacity_index):
        point = ((roll_die() + self.stat[capacity_index]) / (40 * self.get_level()))
        if point >= 0.75:
            return 3 # succès critique
        elif point >= 0.5:
            return 2 # succès
        elif point >= 0.25:
            return 1 # échec
        else: return 0 # échec critique

    def get_stat(self):
        return [self.name, self.species, self.get_level()] + self.stat + [self.place, [(i.name, i.quantity) for i in self.inventory], self.note, self.avatar, [i.name for i in self.power]]

    # Du courage à la mana (incluse)
    def stat_add(self, stat_to_add):
        for i in range(7): self.capacity_modify(i, stat_to_add[i])
        self.max_weight = 10 * self.stat[1]

    def stat_sub(self, stat_to_sub):
        for i in range(7): self.capacity_modify(i, -stat_to_sub[i])
        self.max_weight = 10 * self.stat[1]

    def have(self, object_name): # Renvoie : (index, Object), Object.type = -1 si l'objet est inconnu ; index = -1 si l'objet n'est pas possédé
        object_name = get_official_name(object_name, True)
        for index, obj in enumerate(self.inventory):
            if object_name == obj.official_name:
                return index, obj

        return -1, get_object(object_name)

    def object_add(self, object_name, nb):
        index, obj = self.have(object_name)

        # Objet stockable en plusieurs exemplaire
        if obj.object_type in (1, 5):
            self.stat[8] += nb * obj.stat[8]

            if index + 1: # Objet déjà possédé
                self.inventory[index].quantity += nb
            else: # Pas encore possédé
                obj.quantity = nb
                self.inventory.append(obj)
            return 1

        elif index == -1: # Si stockable en un seul exemplaire et que l'objet n'est pas dans l'inventaire
            obj.name = object_name
            self.stat[8] += obj.stat[8]
            obj.quantity = 1
            if obj.object_type != 2: self.inventory.append(obj)
            if obj.object_type in (0, 2): self.stat_add(obj.stat)
            return 2

        else:
            return 0

    def object_del(self, object_name, nb, force_mode=False):
        index, obj = self.have(object_name)

        # Objet non possédé ou pas en assez grande quantité
        if index == -1 or (self.inventory[index].quantity < nb and not force_mode):
            return 0

        else:
            if nb > self.inventory[index].quantity: nb = self.inventory[index].quantity
            self.stat[8] -= nb * obj.stat[8]
            self.inventory[index].quantity -= nb
            if self.inventory[index].quantity <= 0: self.inventory.pop(index)
            if obj.object_type == 0: self.stat_sub(obj.stat)
            return 1

    def object_use(self, object_name, nb):
        index, obj = self.have(object_name)

        # Objet non possédé ou pas en assez grande quantité
        if index == -1 or self.inventory[index].quantity < nb:
            return 0

        if obj.object_type in (1, 5):
            self.stat[8] -= nb * obj.stat[8]
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
        if not power:
            # Pouvoir non enregistré
            return 0
        elif power.power_id in [i.power_id for i in self.power] or len(self.power) >= 3:
            # Pouvoir déjà possédé
            return 1
        else:
            self.power.append(power)
            # Succès
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

