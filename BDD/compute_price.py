import sqlite3


def get_price(stat):
	return sum(stat)


def compute():
	table = sqlite3.connect("odyssee_objects.db")
	c = table.cursor()
	database = c.execute("SELECT * FROM objets").fetchall()

	for obj in database:
		# si l'objet n'est rattaché à aucun magasin
		if obj[0] == -1: price = 0
		
		# sinon
		else:
			price = get_price(obj[3: -2])
			if price == 0: price = 1
			elif price < 0: price = abs(price)
		
		# si l'objet n'est ni un moyen de transport, ni un outil, ni une matière première on met à jour
		if not obj[1] in (6, 7, 8):
			c.execute(f"""
				UPDATE objets SET argent = {price}
				WHERE nom = \"{obj[2]}\"
				""")
	table.commit()
	table.close()

compute()
