import sqlite3


def get_travel_mean(mean_name):
    table = sqlite3.connect("BDD/odyssee_travel.db")
    c = table.cursor()

    database = c.execute(
        f'SELECT km_heure, par_jour, mer FROM moyens_transport WHERE nom = "{mean_name.lower()}"'
    ).fetchall()
    table.close()

    if database:
        return database[0]
    else:
        return -1, -1, -1


def get_all_travel_mean():
    table = sqlite3.connect("BDD/odyssee_travel.db")
    c = table.cursor()

    database = c.execute(f"SELECT nom FROM moyens_transport").fetchall()
    table.close()

    return ", ".join([i[0] for i in database])


def get_weather(weather_name):
    table = sqlite3.connect("BDD/odyssee_travel.db")
    c = table.cursor()

    database = c.execute(
        f'SELECT sur_terre, sur_mer FROM meteo WHERE nom = "{weather_name.lower()}"'
    ).fetchall()
    table.close()

    if database:
        return database[0]
    else:
        return -1, -1


def get_all_weather():
    table = sqlite3.connect("BDD/odyssee_travel.db")
    c = table.cursor()

    database = c.execute(f"SELECT nom FROM meteo").fetchall()
    table.close()

    return ", ".join([i[0] for i in database])


def get_landtype(landtype_name):
    table = sqlite3.connect("BDD/odyssee_travel.db")
    c = table.cursor()

    database = c.execute(
        f'SELECT route, chemin, hors_piste FROM terrain WHERE nom = "{landtype_name.lower()}"'
    ).fetchall()
    table.close()

    if database:
        return database[0]
    else:
        return None


def get_all_landtype():
    table = sqlite3.connect("BDD/odyssee_travel.db")
    c = table.cursor()

    database = c.execute(f"SELECT nom FROM terrain").fetchall()
    table.close()

    return ", ".join([i[0] for i in database])
