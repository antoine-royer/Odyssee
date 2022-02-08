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

	return " ".join([i for i in string.split(" ") if i])


def get_properties(properties):
	index = 0
	while properties[index].name != "h2": index += 1
	
	clean_properties = []
	write_index = -1
	write_check = True
	for i in properties[: index]:
		if i.name == "h3":
			clean_properties.append([])
			write_index += 1
			write_check = True
			clean_properties[write_index].append(clean(i.text))
		
		else:
			prop = clean(i.text)
			if prop and not prop in clean_properties[write_index] and write_check:
				clean_properties[write_index].append("\n".join([f" ❖ {j}" for j in prop.split("\n")]))
				write_check = False

	return clean_properties


def wikiphyto_api(plant_name):
	url = f"http://www.wikiphyto.org/wiki/{plant_name}"
	page = requests.get(url)
	status_code = page.status_code
	url = page.url
	page = BeautifulSoup(page.text, features="html5lib")
	
	check_code, suggestion = check_search(page)
	if check_code == 0: return suggestion, 0
	elif check_code == 1 or status_code != 200: return None, 1
	
	try:
		img = f"http://www.wikiphyto.org{page.find('img', {'class': 'thumbimage'}).get('src')}"
	except:
		img = None
	
	latin_name = page.find("span", {"id": "D.C3.A9nomination_latine_internationale"}).find_next().text
	family = page.find("span", {"id": "Famille_botanique"}).find_next().text
	
	description = page.find("span", {"id": "Description_et_habitat"}).find_next().text
	if len(description) > 1000: description = description[: 1000] + "…"
	description = [f" ❖ {clean(i)}" for i in description.split("\n")]

	used_parts = page.find("span", {"id": "Parties_utilis.C3.A9es"}).find_next().text
	if len(used_parts) > 1000: used_parts = used_parts[: 1000] + "…"
	used_parts = [f" ❖ {clean(i)}" for i in used_parts.split("\n")]

	properties = get_properties(page.find("span", {"id": "Propri.C3.A9t.C3.A9s"}).find_all_next())
	
	return (clean(latin_name), clean(family), description, used_parts, properties, img, url), 2