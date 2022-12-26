import sqlite3

table = sqlite3.connect("odyssee_powers.db")
c = table.cursor()
database = c.execute("SELECT nom, description, cout_mana FROM pouvoirs").fetchall()
table.close()

latex_code = r"""\begin{supertabular}{|c|c|c|} \hline
Nom du sorts & description & coût P \\ \hline \hline
"""

for (nom, desc, pm) in database:
	latex_code += f"{nom} & {desc} & {pm}" + r"\\ \hline" + "\n"

latex_code += r"\end{supertabular}"
with open("latex_obj.tex", "w") as file:
	file.write(latex_code)
	file.close()
