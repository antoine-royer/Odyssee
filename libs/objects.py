import sqlite3


# --- Constructeur des objets --- #


class Object:
    def __init__(self, name, official_name, stat, object_type, shop_id, quantity=-1):
        self.name = name
        self.official_name = official_name
        self.stat = list(stat)
        self.object_type = object_type
        self.shop_id = shop_id
        self.quantity = quantity

    def export(self):
        return [self.name, self.official_name, self.stat, self.object_type, self.shop_id, self.quantity]



def get_shop_name():
    return (
        ("auberge", "gargote", "taverne", "hôtel", "bar"),
        ("forge", "armurerie"),
        ("officine", "herboristerie", "pharamacie"),
        ("tannerie", "maroquinerie"),
        ("écurie", "haras", "ferme"),
        ("port", "accastillage"),
        ("librairie", "bibliothèque", "libraire", "bouquiniste"),
        ("orfèvre", "bijoutier")
    )


def get_all_types():
    table = sqlite3.connect("BDD/odyssee_objects.db")
    c = table.cursor()

    database = c.execute("SELECT id, description FROM types").fetchall()
    table.close()

    return database


# object_stat : renvoie les stats d'un objets sous la forme : (nom, stat, isknown) où isknow = -1 si l'objet n'est pas connu; type de l'objet sinon
def get_object(object_name, shop_id=None):
    table = sqlite3.connect("BDD/odyssee_objects.db")
    c = table.cursor()

    if shop_id:
        database = c.execute(f"""
            SELECT nom, courage, force, habilete, rapidite, intelligence, defense, vie, mana, argent, poids, type, magasin FROM objets
            WHERE nom = \"{object_name}\" AND magasin = {shop_id}
        """).fetchall()
    else:
        database = c.execute(f"""
            SELECT nom, courage, force, habilete, rapidite, intelligence, defense, vie, mana, argent, poids, type, magasin FROM objets
            WHERE nom = \"{object_name}\"
        """).fetchall()
    table.close()

    if database:
        database = database[0]
        return Object(object_name, database[0], list(database[1: -2]), database[-2], database[-1]) 
    else:
        return Object(object_name, object_name, [int(i == 9) for i in range(10)], -1, -1)


def get_official_name(object_name, return_entry=False):
    table = sqlite3.connect("BDD/odyssee_objects.db")
    c = table.cursor()

    database = c.execute("SELECT nom FROM objets").fetchall()
    table.close()
    object_name = object_name.lower()
    match = {len(name[0]): name[0] for name in database if name[0] in object_name}

    if match:
        return match[max(match.keys())]
    elif return_entry:
        return object_name
    else:
        return None


def get_object_by_shop(shop_id):
    table = sqlite3.connect("BDD/odyssee_objects.db")
    c = table.cursor()

    database = c.execute(f"""
        SELECT nom, courage, force, habilete, rapidite, intelligence, defense, vie, mana, argent, poids, type, magasin FROM objets
        WHERE magasin = {shop_id}
        """).fetchall()
    table.close()

    return [Object(i[0], i[0], i[1:-2], i[-2], i[-1]) for i in database]


def get_type_by_id(type_id):
    table = sqlite3.connect("BDD/odyssee_objects.db")
    c = table.cursor()

    database = c.execute(f"""
        SELECT description FROM types
        WHERE id = {type_id}  
        """).fetchall()
    table.close()

    if database: return database[0][0]

