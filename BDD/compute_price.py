import sqlite3


def get_price(stat):
	return sum(stat)


def compute():
	table = sqlite3.connect("odyssee_objects.db")
	c = table.cursor()
	database = c.execute("SELECT * FROM objets").fetchall()

	for obj in database:
		if obj[0] == -1:
			price = 0
		
		else:
			price = get_price(obj[3: -2])
			if price == 0: price = 1
			elif price < 0: price = abs(price)
		
		if obj[1] != 6:
			c.execute(f"""
				UPDATE objets SET argent = {price}
				WHERE nom = \"{obj[2]}\"
				""")
	table.commit()
	table.close()

compute()
