import sqlite3


def get_state_by_id(state_id):
    table = sqlite3.connect("BDD/odyssee_states.db")
    c = table.cursor()

    result = c.execute(
        f"""
        SELECT nom FROM etats
        WHERE id = {state_id}
        """
    ).fetchall()
    table.close()

    if result:
        return result[0][0]
    else:
        return None


def get_state_by_name(state_name):
    table = sqlite3.connect("BDD/odyssee_states.db")
    c = table.cursor()

    result = c.execute(
        f"""
        SELECT id FROM etats
        WHERE nom_ref LIKE '{state_name}%'
        """
    ).fetchall()
    table.close()

    if result:
        return result[0][0]
    else:
        return -1


def get_states_list():
    table = sqlite3.connect("BDD/odyssee_states.db")
    c = table.cursor()

    result = c.execute("SELECT nom FROM etats").fetchall()
    table.close()

    return [i[0] for i in result]
