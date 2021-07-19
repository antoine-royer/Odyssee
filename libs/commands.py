import discord
from discord.ext import commands

import requests
from bs4 import BeautifulSoup
from libs.lib_odyssee import *


guild_id = None


async def server_id(ctx):
    global guild_id

    if not guild_id:
        guild_id = ctx.guild.id
    if guild_id != ctx.guild.id:
        await send_error(ctx, "Odyssée est utilisé sur un autre serveur")

    return guild_id == ctx.guild.id



class OdysseeCommands(commands.Cog):
    def __init__(self, config, savefile):
        global guild_id
        self.data_player, self.data_kick, guild_id = savefile
        self.PREFIX = config["PREFIX"]


    def save_game(self):
        for player_id in self.data_player:
            player = self.data_player[player_id]
            player.max_weight = 5 * (player.stat[1] + 1)
        export_save(self.data_player, self.data_kick, guild_id)


    def get_player_from_id(self, player_id):
        if player_id in self.data_player:
            return self.data_player[player_id]
        else:
            return None


    def get_player_from_name(self, player_name):
        for player_id in self.data_player:
            if self.data_player[player_id].name == player_name:
                return self.data_player[player_id]
        return None


    @commands.command(help="Affiche l'aide ou l'aide détaillée.", brief="Affiche ce panneau")
    async def aide(self, ctx, commande: str=None):

        def get_syntax(cmnd):
            syntax = f"`{self.PREFIX}{cmnd.name}"
            for arg in cmnd.clean_params:
                if "=" in str(cmnd.clean_params[arg]):
                    syntax+= f" [{arg}]"
                else:
                    syntax += f" <{arg}>"
            return syntax + "`"
            
        if commande:
            embed = discord.Embed(title="Aide détaillée", description="Informations complémentaires", color=8421504)
            cmnd_data = {cmnd.name: cmnd for cmnd in self.get_commands()}

            if commande in cmnd_data:
                cmnd = cmnd_data[commande]
                embed.add_field(name="Syntaxe", value=get_syntax(cmnd), inline=True)
                embed.add_field(name="Description", value=cmnd.help, inline=True)
            else:
                embed.add_field(name="Erreur : commande inconnue", value=f"Entrez `{self.PREFIX}aide` pour avoir la liste des commandes.")
        
        else:
            embed = discord.Embed(title="Rubrique d'aide", description=f"Entrez : `{self.PREFIX}aide <commande>` pour plus d'informations.", color=8421504)
            for cmnd in self.get_commands():
                embed.add_field(name=cmnd.brief, value=get_syntax(cmnd), inline=False)
        await ctx.send(embed=embed)


    @commands.command(help="Votre espèce est à préciser impérativement. Si aucun pseudonyme n'est précisé, Odyssée prendra votre nom d'utilisateur.", brief="Créer un nouveau joueur")
    @commands.check(server_id)
    async def nouveau(self, ctx, espece: str, nom: str=None):
        user = get_user(ctx)

        if user[1] in self.data_kick:
            await ctx.send(f"*Erreur : {user[0]} a été kické.*")
            return
        
        if not nom: nom = user[0]

        if not user[1] in self.data_player:
            self.data_player.update({user[1] : Player(user[1], nom, espece, str(ctx.author.avatar_url))})
            await ctx.send(f"{nom}, un(e) {espece}, est apparu(e).")
        else:
            await ctx.send(f"*Erreur : {user[0]} est déjà enregistré(e).*")

        self.save_game()


    @commands.command(help="Permet de changer son pseudo dans le jeu. Le pseudo utilisé avec Odyssée n'a aucun rapport avec celui du serveur Discord.", brief="Changer de pseudo")
    @commands.check(server_id)
    async def pseudo(self, ctx, nom: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if not self.get_player_from_name(nom):
            await ctx.send(f"__{player.name}__ s'appelle désormais : {nom}")
            player.name = nom
        else:
            await send_error(ctx, "ce pseudo est déjà pris")

        self.save_game()


    @commands.command(help="Changer sa couleur. En format de couleur, vous pouvez donner le code RVB en hexadécimal ou entrer le nom de la couleur voulue (voir les noms sur le site : http://www.proftnj.com/RGB3.htm).", brief="Changer sa couleur")
    @commands.check(server_id)
    async def couleur(self, ctx, couleur: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if couleur.startswith("0x"):
            couleur = int(couleur, 16)
            player.stat[9] = couleur
            await ctx.send(f"La couleur de __{player.name}__ a été changée avec succès.")
        else:
            colors = requests.get("http://www.proftnj.com/RGB3.htm").text
            colors = {colors.text: f"{colors.get('value').lower()}" for colors in BeautifulSoup(colors, features="html5lib").find_all("option")}
            
            if couleur in colors:
                player.stat[9] = int(colors[couleur], 16)
                await ctx.send(f"La couleur de __{player.name}__ est devenue : {couleur}.")
            else:
                await send_error(ctx, f"couleur inconnue : '{couleur}'. Pour avoir la liste des couleurs disponible : http://www.proftnj.com/RGB3.htm")

        self.save_game()


    @commands.command(help="Changer de lieu.", brief="Changer de lieu")
    @commands.check(server_id)
    async def lieu(self, ctx, lieu: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        player.place = lieu
        await ctx.send(f"__{player.name}__ se dirige vers {lieu}.")

        self.save_game()


    @commands.command(help="Voir ses statistiques, spécifier un nom de joueur permet de voir les statististiques du joueur ciblé.", brief="Voir ses statistiques")
    @commands.check(server_id)
    async def stat(self, ctx, joueur: str=None):
        if joueur: joueur = self.get_player_from_name(joueur)
        else: joueur = self.get_player_from_id(ctx.author.id)

        if not joueur:
            await send_error("vous n'êtes pas un joueur enregistré ou le joueur dont vous voulez voir les statististiques n'existe pas")
            return
    
        # Embed's construction
        info = joueur.get_stat()
        embed = discord.Embed(title=info[0], description=f"Statistiques de {info[0]}, {info[1]}\n de niveau {info[2]}", color=info[12])
        if info[16]: embed.set_thumbnail(url=info[16])
        
        # Capacities
        capacities = ""
        for index, capacity_name in enumerate(("Courage .", "Force ...", "Habileté ", "Rapidité ", "Défense .")):
            capacities += f"`{capacity_name}.: {info[3 + index]}`\n"

        # Misceleanous
        misc = ""
        for index, misc_name in enumerate(("Vie ...# PV", "Mana ..#", "Argent # Drachmes", f"Poids .# / {joueur.max_weight}")):
            before, after = misc_name.split("#")
            misc += f"`{before}.: {info[index + 8]}{after}`\n"

        # Inventory
        if len(info[14]):
            inventory = ""
            for item in info[14]:
                inventory += f" ❖ {item[0]} {('', f' ({item[1]})')[item[1] > 1]}\n"
        else:
            inventory = "< vide >"

        # Powers
        if info[17]:
            powers = ""
            for i in info[17]:
                powers += f" ❖ {i.capitalize()}\n"
        else:
            powers = "< aucun >"

        # Notes
        if info[15][0][0]:
            note = "\n".join([f"{i[0]} - {i[1]}" for i in info[15]])
        else:
            note = "< aucune >"

        embed.add_field(name="Capacités", value=capacities, inline=True)
        embed.add_field(name="Divers", value=misc, inline=True)
        embed.add_field(name="Lieu", value=info[13], inline=True)
        embed.add_field(name="Inventaire", value=inventory, inline=True)
        embed.add_field(name="Pouvoirs", value=powers, inline=True)
        embed.add_field(name="Notes", value=note, inline=True)

        await ctx.send(embed=embed)


    @commands.command(help="Permet de gérer ses notes.\n\n`contenu` peut être soit une chaîne de caractères si l'on veux ajouter une note, soit l'indice de la note que l'on veut supprimer.", brief="Gérer ses notes")
    @commands.check(server_id)
    async def note(self, ctx, contenu):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        contenu = int_converter(contenu)

        if type(contenu) == str:
            player.add_note(contenu)
            await ctx.send(f"____{player.name}____ a ajouté la note :\n> {contenu}")

        elif type(contenu) == int and contenu > 0:
            check = player.del_note(contenu)
            if check:
                await ctx.send(f"____{player.name}____ a supprimé la note :\n> {check}")
            else:
                await ctx.send(f"*Erreur : la note n°{contenu} n'existe pas.*")

        self.save_game()


    @commands.command(help="Voir la liste des joueurs enregistrés", brief="Voir les joueurs enregistrés")
    @commands.check(server_id)
    async def liste(self, ctx):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        embed = discord.Embed(title="Joueurs", description="Liste des joueurs enregistrés", color=player.stat[9])
        for player_id in self.data_player:
            player = self.data_player[player_id]
            embed.add_field(name=player.name, value=f"{player.species} de niveau {player.get_level()} vers {player.place}{('', ' (PnJ)')[player.id <= 0]}", inline=False)
        
        await ctx.send(embed=embed)


    @commands.command(help="Le premier paramètre est le nom de l'objet, le second est optionnel et correspond au nombre d'objets pris.", brief="Prendre un objet")
    @commands.check(server_id)
    async def prend(self, ctx, nom: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if nombre <= 0: nombre = 1
        check = player.object_add(nom, nombre)
        
        if check:
            if check == 1: nombre = f" ({nombre})"
            else: nombre = ""
            await ctx.send(f"__{player.name}__ prend {nom}{nombre}")
        else:
            await send_error(ctx, f"__{player.name}__ possède déjà l'objet : '{nom}'")

        self.save_game()


    @commands.command(help="Jetter un objet, le premier paramètre est le nom de l'objet à jeter, le second est optionnel et correspond au nombre d'objets à jeter.", brief="Jeter un objet")
    @commands.check(server_id)
    async def jette(self, ctx, nom: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if nombre <= 0: nombre = 1
        check = player.object_del(nom, nombre)

        if check == 1:
            if nombre > 1: nombre = f" ({nombre})"
            else: nombre = ""
            await ctx.send(f"__{player.name}__ jette {nom}{nombre}")
        else:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}', ou pas en assez grande quantité")

        self.save_game()


    @commands.command(help="Sert à utiliser un objet (manger de la nourriture ou consommer un bien). Le premier argument est le nom de l'objet à utiliser, le second (optionnel) correspond au nombre d'unité à utiliser.", brief="Utiliser un objet")
    @commands.check(server_id)
    async def utilise(self, ctx, nom: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if nombre <= 0: nombre = 1
        check = player.object_use(nom, nombre)

        if check == 1:
            await ctx.send(f"__{player.name}__ utilise {nom} ({nombre}).")
        elif check == 2:
            await send_error(ctx, f"__{player.name}__ ne peut pas utiliser cet objet : '{nom}'")
        else:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}', ou pas en assez grande qantité")

        self.save_game()


    @commands.command(help="Donner un objet à un joueur. Le premier argument est le nom du joueur, le second le nom de l'objet ('Argent', ou 'Drachmes' pour donner de l'argent). Le dernier paramètre, faculatatif correspond à la quantité donnée (nombre d'unité ou montant).", brief="Donner un objet")
    @commands.check(server_id)
    async def donne(self, ctx, joueur: str, objet: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        target = self.get_player_from_name(joueur)
        if not target: await send_error(ctx, f"{joueur} n'est pas un joueur enregistré"); return


        if player.place != target.place:
            await send_error(ctx, f"__{player.name}__ et __{target.name}__ ne sont pas au même endroit")
            return

        object_name = objet.lower()
        objet = objet.capitalize()
        nombre = abs(nombre)

        if object_name in ("argent", "drachmes"):
            if player.stat[7] >= nombre:
                player.stat[7] -= nombre
                target.stat[7] += nombre
                await ctx.send(f"__{player.name}__ donne {nombre} Drachme{('', 's')[nombre > 1]} à __{target.name}__.")
            else:
                await send_error(ctx, f"__{player.name}__ n'a pas assez de Drachmes pour donner")
        
        else:
            check_player = player.object_del(object_name, nombre)
            check_target = target.object_add(object_name, nombre)
            is_ok = True

            if not check_player:
                await send_error(ctx, f"__{player.name}__ ne possède pas cet objet : '{objet}' ou pas en assez grande quantité")
                if check_target: target.object_del(object_name, nombre, True)
                is_ok = False

            if not check_target:
                await send_error(ctx, f"__{target.name}__ a déjà cet objet : '{objet}'")
                if check_player: player.object_add(object_name, nombre)
                is_ok = False

            if is_ok:
                nombre = ("", f" ({nombre})")[nombre > 1]
                await ctx.send(f"__{player.name}__ a donné {objet}{nombre} à __{target.name}__.")

        self.save_game()


    @commands.command(name="dé", help="Lancer un dé. Le premier paramètre est le nombre de faces du dé (> 3), le second est le nombre de dés lancés. Les deux paramètres sont optionnels, par défault, un dé à 20 faces est lancé.", brief="Lancer un dé")
    @commands.check(server_id)
    async def de(self, ctx, faces: int=20, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if faces < 4: faces = 4
        if nombre < 1: nombre = 1
        result = randint(nombre, nombre * faces)

        await ctx.send(f"__{player.name}__ lance {nombre} dé{('', 's')[nombre > 1]} à {faces} faces : {result} / {nombre * faces}.")


    @commands.command(help="Effectue un lancer dans dans une capacité (Courage, Force, Habileté, Rapidité, Défense).", brief="Effectuer un lancer dans une capacité")
    @commands.check(server_id)
    async def lancer(self, ctx, capacite: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        capacities = ("Courage", "Force", "Habileté", "Rapidité", "Défense")

        if not capacite.capitalize() in capacities:
            await send_error(ctx, f"la capacité '{capacite}' n'est pas connue.")
            return

        index = capacities.index(capacite.capitalize())
        comment = ("échec critique", "échec", "succès", "succès critique")[player.capacity_roll(index)]
        await ctx.send(f"__{player.name}__ a fait un {comment} sur son lancer " + ("de ", "d'")[index == 2] + capacities[index])

    
    @commands.command(help="Utiliser ou consulter ses pouvoirs. Le premier argument est le nom du pouvoir à utiliser, le second correspond au nom de l'adversaire visé (dans le cas où le pouvoir utilisé requiert un adversaire).\n\n Si vous laissez ses deux argments vide, vous obtenez la liste de vos pouvoirs avec une description.", brief="Utiliser ou consulter ses pouvoirs")
    @commands.check(server_id)
    async def pouvoir(self, ctx, nom: str=None, adversaire: str=None):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if adversaire:
            adversaire = self.get_player_from_name(adversaire)
            if not adversaire: await send_error(ctx, f"{adversaire} n'est pas un joueur enregistré"); return

        if nom:
            power = get_power_by_name(nom.lower())
            nom = nom.capitalize()

            if not power: await send_error(ctx, f"le pouvoir '{nom}' n'existe pas"); return
            if power.power_id not in [i.power_id for i in player.power]: await send_error(ctx, f"__{player.name}__ ne possède pas le pouvoir : '{nom}'"); return
            if player.stat[6] <= 0: await ctx.send(f"__{player.name}__ tente d'utiliser {nom}, mais échoue."); return
            if power.enemy and not adversaire: await send_error(ctx, f"le sort '{nom}' nécessite une cible"); return

            player.stat[6] -= 1
            await ctx.send(f"__{player.name}__ utilise {nom} :\n" + power_use(power.power_id)(player, self.data_player, adversaire))

        else:
            embed = discord.Embed(title=f"Pouvoirs de {player.name}", description="Pouvoirs spéciaux connus et descriptions", color=player.stat[9])
            
            for power in player.power:
                description = power.description + ("", "(adversaire requis)")[power.enemy]
                embed.add_field(name=power.name.capitalize(), value=power.description, inline=False)
            
            await ctx.send(embed=embed)


    @commands.command(help="Vous permer d'apprendre de nouveau sort. le nom du sort est obligatoire.", brief="Apprend un nouveau pouvoir spécial")
    @commands.check(server_id)
    async def apprend(self, ctx, nom: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        check = player.power_add(nom.lower())
        nom = nom.capitalize()

        if check == 0:
            await send_error(ctx, f"le pouvoir '{nom} n'existe pas")
        elif check == 1:
            await send_error(ctx, f"__{player.name}__ a déjà le pouvoir : '{nom}' ou vous avez déjà plus de trois pouvoirs")
        else:
            await ctx.send(f"__{player.name}__ apprend le pouvoir : '{nom}'.")

        self.save_game()


    @commands.command(help="Vous permer d'oublier un sort. le nom du sort est obligatoire.", brief="Oublier un pouvoir spécial")
    @commands.check(server_id)
    async def oublie(self, ctx, nom: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        check = player.power_sub(nom.lower())
        nom = nom.capitalize()

        if check == 0:
            await send_error(ctx, f"le pouvoir '{nom} n'existe pas")
        elif check == 1:
            await send_error(ctx, f"__{player.name}__ n'a pas le pouvoir : '{nom}'")
        else:
            await ctx.send(f"__{player.name}__ oublie le pouvoir : '{nom}'.")

        self.save_game()


    @commands.command(help="Vous permet de consulter la liste des articles disponible. Préciser un nom vous renvoie la description détaillée de l'objet demandé.", brief="Voir les articles disponibles")
    @commands.check(server_id)
    async def article(self, ctx, nom: str=None):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        if nom:
            obj = get_object(get_official_name(nom, shop_id))
            if obj.shop_id == -1: await send_error(ctx, f"cet objet : '{nom}' n'est pas vendu ici"); return

            embed = discord.Embed(title=nom, value="Description détaillée", color=player.stat[9])

            capacity = ""
            for index, name in enumerate(("Courage .", "Force ...", "Habileté ", "Rapidité ", "Défense .")):
                capacity += f"`{name}.: {obj.stat[index]}`\n"

            misc = ""
            for index, name in enumerate(("Usage .", "Vie ...# PV", "Mana ..#", "Valeur # Drachmes", "Poids .#")):
                if not index:
                    misc += f"`{name}.: {get_type_by_id(obj.object_type)}`\n"
                else:
                    name = name.split("#")
                    misc += f"`{name[0]}.: {obj.stat[index + 4]}{name[1]}`\n"

            embed.add_field(name="Caractéristiques", value=capacity)
            embed.add_field(name="Divers", value=misc)

            await ctx.send(embed=embed)

        else:
            all_objects = get_object_by_shop(shop_id)
            embed = discord.Embed(title=player.place, description="Liste des articles disponible", color=player.stat[9])
            for obj in all_objects:
                capacity = ("Courage", "Force", "Habileté", "Rapidité", "Défense", "Vie", "Mana", "Valeur", "Poids")
                capacity = "; ".join([f"{name} : {obj.stat[index]}" for index, name in enumerate(capacity) if obj.stat[index]])
                embed.add_field(name=obj.name.capitalize(), value=capacity, inline=False)

            await ctx.send(embed=embed)


    @commands.command(help="Vous permer d'acheter des objets. Le premier paramètre est le nom de l'objet, le second, faculatatif, est le nombre d'objet à acheter.", brief="Acheter un objet")
    @commands.check(server_id)
    async def achat(self, ctx, nom: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        obj = get_object(get_official_name(nom.lower()), shop_id)
        if obj.shop_id == -1: await send_error(ctx, f"cet objet : '{nom}' n'est pas vendu ici"); return

        if obj.object_type not in (1, 5) or nombre < 1: nombre = 1

        if player.stat[7] >= nombre * obj.stat[7]:
            check = player.object_add(nom, nombre)

            if check:
                player.stat[7] -= nombre * obj.stat[7]
                nb = ("", f" ({nombre})")[nombre > 1]
                await ctx.send(f"__{player.name}__ a acheté l'objet : '{nom}{nb}' pour {nombre * obj.stat[7]} Drachmes.")
            else:
                await send_error(ctx, f"__{player.name}__ a déjà cet objet : '{nom}'")

        else:
            await send_error(ctx, f"__{player.name}__ n'a pas assez de Drachmes pour acheter cet objet : '{nom}'")


        self.save_game()


    @commands.command(help="Permet de vendre un objet. Le nom est à préciser, le nombre d'unité à vendre est facultatif (1 par défaut)", brief="Vendre un objet")
    @commands.check(server_id)
    async def vend(self, ctx, nom: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        obj = get_object(get_official_name(nom.lower()), shop_id)
        if obj.shop_id == -1: await send_error(ctx, f"l'objet : '{nom}' n'est pas vendable ici"); return

        if obj.object_type not in (1, 5) or nombre < 1: nombre = 1

        check = player.object_del(nom, nombre)

        if check:
            cost = (3 * nombre * obj.stat[7]) // 4
            nombre = ("", f" ({nombre})")[nombre > 1]
            player.stat[7] += cost
            await ctx.send(f"__{player.name}__ a vendu l'objet : '{nom}{nombre}' pour {cost} Drachmes.")
        else:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}', ou pas en assez grande quantité")

        self.save_game()


    @commands.command(help=f"Calculer la vitesse nécessaire pour parcourir une certaine distance.\n\n__Moyens de transport__ : {get_all_travel_mean()}\n\n__Météo__ : {get_all_weather()}\n\n__Terrains__ : {get_all_landtype()}", brief="Calculer un temps de trajet")
    @commands.check(server_id)
    async def temps(self, ctx, distance: int, moyen_transport: str, meteo: str, terrain: str=None):
        
        per_hour, per_day, on_sea = get_travel_mean(moyen_transport)
        weather = get_weather(meteo)[on_sea]

        if per_hour == -1:
            await send_error(ctx, "moyen de transport inconnu"); return
        if weather == -1:
            await send_error(ctx, "météo inconnue"); return

        per_day *= weather
        per_hour *= weather

        if on_sea:
            embed = discord.Embed(title="Temps", description=f"Temps nécessaire pour parcourir {distance} km", color=8421504)
            embed.add_field(name="Sur la mer", value=f"`jour(s) ..: {int(distance // per_day)}`\n`heure(s) .: {int(distance % per_day // per_hour)}`", inline=False)
            await ctx.send(embed=embed)

        else:
            if not terrain: await send_error(ctx, "terrain inconnu"); return

            embed = discord.Embed(title="Temps", description=f"Temps nécessaire pour parcourir {distance} km", color=8421504)
            land_name = ("Sur une route", "Sur un chemin", "Hors piste")

            for index, land_type in enumerate(get_landtype(terrain)):
                embed.add_field(name=land_name[index], value=f"`jour(s) ..: {int(distance // (per_day * land_type))}`\n`heure(s) .: {int(distance % (per_day * land_type) // per_hour)}`", inline=False)

            await ctx.send(embed=embed)


    @commands.command(help=f"Génère une liste de noms aléatoire selon une catégorie donnée parmi la liste : {get_categories()}.", brief="Génère des noms aléatoire")
    @commands.check(server_id)
    async def nom(self, ctx, categorie: str="human", nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        categorie = categorie.lower()

        if nombre <= 0: nombre = 1
        elif nombre > 10: nombre = 10

        names = requests.get(f"https://www.nomsdefantasy.com/{categorie}/medium").text
        names = [names.contents[0] for names in BeautifulSoup(names, features="html5lib").find_all("li")]
        
        embed = discord.Embed(title="Générateur de nom", description=f"Nom{('', 's')[nombre > 1]} '{categorie}' au hasard", color=player.stat[9])
        embed.add_field(name="Noms", value=" ❖ " + "\n ❖ ".join(names[:nombre]))
        await ctx.send(embed=embed)


    @commands.command(help="Commencer ou continuer un combat. Précisez le nom de l'adversaire et l'arme utilisée.", brief="Combattre")
    @commands.check(server_id)
    async def combat(self, ctx, adversaire: str, arme: str=None):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        # Verification de l'existence de la cible, et création d'icelle dans le cas échéant
        target = self.get_player_from_name(adversaire)

        if not target:
            new_player_id = -len(self.data_player)
            level = get_avg_level(self.data_player)
            stat = stat_gen([1 for _ in range(4)], randint(level, 2 * level), True)
            self.data_player.update({new_player_id : Player(new_player_id, adversaire, "Ennemi", "", stat, player.place)})
            self.save_game()

            await ctx.send(f"__{player.name}__ se prépare à combattre __{adversaire}__.")
            return

        # Vérification de l'arme du joueur
        if arme:
            index, player_weapon = player.have(arme)

            # si le joueur n'a pas l'arme demandée
            if index == -1:
                await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{arme}'")
                return

            # si c'est une arme connue
            elif player_weapon.object_type in (3, 4):

                # arme de mêlée => même lieu
                if player_weapon.object_type == 3 and target.place != player.place:
                    await send_error(ctx, f"__{player.name}__ et __{target.name}__ ne sont pas au même endroit")
                    return

                # arme à distance => nécessite un projectile
                if player_weapon.object_type == 4:
                    arrow_index = player.select_object_by_type(5)
                    if arrow_index == -1:
                        await send_error(ctx, f"__{player.name} n'a pas de projectile pour tirer")
                        return
                    else:
                        player.inventory[arrow_index].quantity -= 1

            # si il s'agit d'un objet quelconque
            else:
                player_weapon = Object("", "", [int(i == 8) for i in range(9)], -1, -1)
        
        else:
            if target.place != player.place:
                await send_error(ctx, f"__{player.name}__ et __{target.name}__ ne sont pas au même endroit")
                return
            else: player_weapon = Object("", "", [int(i == 8) for i in range(9)], -1, -1)


        player.stat_add(player_weapon.stat)


        # Arme de l'adversaire
        target_weapon = target.select_object_by_type(3, 4)
        target_can_fight = True

        if target_weapon == -1: target_weapon = Object("", "", [int(i == 8) for i in range(9)], -1, -1)
        else: target_weapon = target.inventory[target_weapon]
        
        if target_weapon.object_type == 4:
            index = target.select_object_by_type(5)
            if index != -1:
                target.inventory[index].quantity -= 1
            else:
                target_can_fight = False

        elif target.place != player.place:
            target_can_fight = False

        target.stat_add(target_weapon.stat)

        # Qui commence
        fighters, target_index = phase_1(player, target)

        message = ""

        for attacker in range(2):
            defender = (attacker + 1) % 2

            turn = True
            if attacker == target_index and not target_can_fight:
                message += f"__{fighters[target_index].name}__ ne peut pas se battre.\n"
                turn = False

            if turn:
                message += f"__{fighters[attacker].name}__ attaque"

                if phase_2(fighters[attacker]):
                    message += " et touche sa cible.\n"

                    damage = phase_3(fighters, attacker, defender)
                    if damage:
                        message += f"__{fighters[defender].name}__ subit {damage} point de dégâts.\n"
                    else:
                        message += f"__{fighters[defender].name}__ esquive le coup.\n"

                    end = False
                    if not fighters[defender].isalive():
                        loot = f"__{fighters[defender].name}__ est mort, __{fighters[attacker].name}__ fouille le cadavre et trouve :\n"
                        if fighters[defender].stat[7]:
                           loot += f" ❖ {fighters[defender].stat[7]} Drachme{('', 's')[fighters[defender].stat[7] > 1]}\n"

                        fighters[attacker].stat[7] += fighters[defender].stat[7]
                        
                        for obj in fighters[defender].inventory:
                            check = fighters[attacker].object_add(obj.name, obj.quantity)
                            if check: loot += f" ❖ {obj.name}{('', f' ({obj.quantity})')[obj.quantity > 1]}\n"

                        self.data_player.pop(fighters[defender].id)

                        message += loot
                        end = True
                else:
                    message += f" et manque sa cible.\n"

            await ctx.send(message)
            if end: break

        player.stat_sub(player_weapon.stat)
        target.stat_sub(target_weapon.stat)

        self.save_game()


    @commands.command(help="Vous permet de vous reposer lorsque vous dormez dehors.", brief="Dormir")
    @commands.check(server_id)
    async def dormir(self, ctx):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        places = [player.place for player in self.data_player.values() if player.id < 0]
        if player.place in places:
            await send_error(ctx, f"__{player.name}__ ne peut pas dormir : il y a des ennemis potentiels à proximité")
            return

        if player.stat[5] < 100:
            player.stat[5] += 5
            if player.stat[5] > 100: player.stat[5] = 100

        if player.stat[6] < 5:
            player.stat[6] += 1
            if player.stat[6] > 5: player.stat[6] = 5

        await ctx.send(f"__{player.name}__ dort.")
