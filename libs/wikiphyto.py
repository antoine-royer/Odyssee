import requests
from bs4 import BeautifulSoup

def check_search(page):
	if "Cette page d’homonymie répertorie les différents sujets et articles partageant un même nom." in page.text:
		urls = []
		for i in page.find("ul").find_all("li"):
			url = i.find("a")
			if not "redlink=1" in url.get("href"): urls.append(f"{url.get('title')}\n")
		return 0, urls
	elif "Il n'y a pour l'instant aucun texte sur cette page." in page.text:
		return 1, None
	else:
		return 2, None


def clean(string):
	while "[" in string and "]" in string:
		start = string.find("[")
		end = string.find("]", start) + 2
		string = string[: start] + string[end: ]

	return string		


def wikiphyto_api(plant_name):
	url = f"http://www.wikiphyto.org/wiki/{plant_name}"
	page = requests.get(url)
	status_code = page.status_code
	page = BeautifulSoup(page.text, features="html5lib")
	
	check_code, suggestion = check_search(page)
	if check_code == 0: return suggestion, 0
	elif check_code == 1 or status_code != 200: return None, 1
	
	try:
		img = f"http://www.wikiphyto.org{page.find('img', {'class': 'thumbimage'}).get('src')}"
	except:
		img = None
	
	latin_name = page.find("span", {"id": "D.C3.A9nomination_latine_internationale"}).find_next().text
	
	description = page.find("span", {"id": "Description_et_habitat"}).find_next().text
	if len(description) > 1000: description = description[: 1000] + "…"
	description = [f" ❖ {clean(i)}" for i in description.split("\n")]

	used_parts = page.find("span", {"id": "Parties_utilis.C3.A9es"}).find_next().text
	if len(used_parts) > 1000: used_parts = used_parts[: 1000] + "…"
	used_parts = [f" ❖ {clean(i)}" for i in used_parts.split("\n")]

	
	plant_properties = page.find("span", {"id": "Propri.C3.A9t.C3.A9s_de_la_plante"}).find_next().text
	plant_properties = [f" ❖ {clean(i)}" for i in plant_properties.split("\n")[: 5] if i != "Propriétés du bourgeon"]
	if not plant_properties: plant_properties = ["< aucune >"]

	bud_properties = page.find("span", {"id": "Propri.C3.A9t.C3.A9s_du_bourgeon"}).find_next().text
	bud_properties = [f" ❖ {clean(i)}" for i in bud_properties.split("\n")[: 5] if i != "Propriétés de l'huile essentielle"]
	if not bud_properties: bud_properties = ["< aucune >"]

	oil_properties = page.find("span", {"id": "Propri.C3.A9t.C3.A9s_de_l.27huile_essentielle"}).find_next().text
	oil_properties = [f" ❖ {clean(i)}" for i in oil_properties.split("\n")[: 5] if i != "Indications"]
	if not oil_properties: oil_properties = ["< aucune >"]
	
	return (clean(latin_name), description, used_parts, (plant_properties, bud_properties, oil_properties), img, url), 2