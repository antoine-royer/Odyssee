import sqlite3


def data_shop_name(place):
    shop_data = {
        "auberge": ["auberge", "taverne", "gargote", "hôtel"],
        "forge": ["forge", "armurerie"],
        "officine": ["pharmacie", "herboristerie", "officine", "apothicairerie"],
        "tannerie": ["maroquinerie", "tannerie"],
        "écurie": ["écurie", "haras"],
        "port": ["port"],
        "librairie": ["librairie", "bouquiniste", "libraire", "bibliothèque"],
        "orfèvre": ["orfèvre", "bijoutier"]
    }

    for shop_key, all_shop_name in shop_data.items():
        for name_to_detect in all_shop_name:
            if name_to_detect in place.lower(): return shop_key
    return False


def data_all_objects_from_id(shop_id):
    table = sqlite3.connect("BDD/odyssee_shop.db")
    c = table.cursor()

    answer = c.execute(
        f"""
        SELECT magasins.nom, types.description, objets.nom, courage, force, habilete, rapidite, defense, vie, mana, argent, poids  FROM types, objets 
        JOIN magasins ON magasins.id = magasin 
        WHERE magasin = {shop_id}")
        """).fetchall()
    table.close()
    return answer


def data_get_object(object_name, shop_name=None):
    table = sqlite3.connect("BDD/odyssee_shop.db")
    c = table.cursor()

    object_name = data_search_by_name(object_name, shop_name)

    answer = c.execute(f"""
        SELECT objets.nom, courage, force, habilete, rapidite, defense, vie, mana, argent, poids, type FROM objets
        WHERE objets.nom = "{object_name}"
        """
        ).fetchall()
    table.close()
    if answer: return answer[0]
    return None


def data_search_by_name(object_name, shop_name=None):
    table = sqlite3.connect("BDD/odyssee_shop.db")
    c = table.cursor()

    if shop_name:
        shop_name = data_shop_name(shop_name)
        database = c.execute(f"SELECT objets.nom FROM objets JOIN magasins on magasins.id = objets.magasin WHERE magasins.nom = \"{shop_name}\"").fetchall()
    else:
        database = c.execute("SELECT nom FROM objets").fetchall()
    table.close()

    object_name = object_name.lower()
    match = {len(name[0]): name[0] for name in database if name[0] in object_name}

    if match: return match[max(match.keys())]
    return None


def data_get_shop_id(shop_name):
    table = sqlite3.connect("BDD/odyssee_shop.db")
    c = table.cursor()

    answer = c.execute(f"SELECT id FROM magasins WHERE nom = \"{shop_name}\"").fetchall()
    table.close()
    return answer


def data_get_all_objects(shop_name=None):
    table = sqlite3.connect("BDD/odyssee_shop.db")
    c = table.cursor()

    if shop_name:
        shop_id = data_get_shop_id(data_shop_name(shop_name))[0][0]
        answer = c.execute(f"""
            SELECT objets.nom, courage, force, habilete, rapidite, defense, vie, mana, argent, poids, type FROM objets
            JOIN magasins ON id = magasin
            WHERE id = {shop_id}
            """
            ).fetchall()
    else:
        answer = c.execute("SELECT nom, courage, force, habilete, rapidite, defense, vie, mana, argent, poids, type FROM objets").fetchall()

    table.close()
    return answer


# object_stat = id du magasin, id du type, nom, courage, force, habileté, rapidité, défense, vie, mana, argent, poids
def data_add_object(object_stat):
    table = sqlite3.connect("BDD/odyssee_shop.db")
    c = table.cursor()

    object_stat[10] = -abs(object_stat[10])

    request = f"INSERT INTO objets VALUES ("
    for index, i in enumerate(object_stat):
        if index == 2: request += f"\"{i.lower()}\", "
        else: request += f"{i}, "
    request = request[:-2] + ")"

    c.execute(request)
    table.commit()
    table.close()
