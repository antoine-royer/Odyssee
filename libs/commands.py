import discord
from discord.ext import commands

import requests
from bs4 import BeautifulSoup
from libs.lib_odyssee import *


guild_id = None
glb_players = {}


def make_embed(fields, title, description, color=8421504, inline=False):
    embeds = []
    nb = len(fields) // 25 + 1
    index = 1
    while fields:
        embed = discord.Embed(title=f"{title} ({index}/{nb})", description=description, color=color)
        for field in fields[: 25]:
            embed.add_field(name=field[0], value=field[1], inline=inline)
        fields = fields[25: ]
        index += 1
        embeds.append(embed)
    return embeds


async def server_id(ctx):
    global guild_id

    if ctx.author.nick: author = ctx.author.nick
    else: author = ctx.author.name
    print(f"{author} : {ctx.message.content}")

    if not guild_id:
        guild_id = ctx.guild.id
    if guild_id != ctx.guild.id:
        await send_error(ctx, "Odyssée est utilisé sur un autre serveur")

    return guild_id == ctx.guild.id


async def awareness(ctx):
    if ctx.author.id not in glb_players:
        await ctx.send(f"{ctx.author.name} n'est pas un joueur enregistré")
        return False

    player = glb_players[ctx.author.id]
    if player.state == 2:
        await ctx.send(f"__{player.name}__ est inconscient(e).")
        return False
    return True


class OdysseeCommands(commands.Cog):
    def __init__(self, config, savefile):
        global guild_id, glb_players
        self.data_player, self.data_kick, guild_id = savefile
        self.PREFIX = config["PREFIX"]

        glb_players = self.data_player


    def save_game(self):
        export_save(self.data_player, self.data_kick, guild_id)


    def get_player_from_id(self, player_id):
        if player_id in self.data_player:
            return self.data_player[player_id]
        else:
            return None


    def get_player_from_name(self, player_name):
        player_name = player_name.lower()
        for player_id in self.data_player:
            if self.data_player[player_id].name.lower() == player_name:
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
            
            await ctx.send(embed=embed)

        else:
            fields = []
            for cmnd in self.get_commands():
                fields.append((cmnd.brief, get_syntax(cmnd)))
            
            for embed in make_embed(fields, "Rubique d'aide", f"Entrez : `{self.PREFIX}aide <commande>` pour plus d'informations."):
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

    @commands.command(help="Vous permet de mettre à jour votre avatar dans les fichiers du bot si vous en changez.", brief="Mettre à jour son avatar")
    @commands.check(server_id)
    async def avatar(self, ctx):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        player.avatar = str(ctx.author.avatar_url)
        await ctx.send(f"L'avatar de __{player.name}__ a été mis à jour.")
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
            player.stat[10] = couleur
            await ctx.send(f"La couleur de __{player.name}__ a été changée avec succès.")
        else:
            colors = requests.get("http://www.proftnj.com/RGB3.htm").text
            colors = {colors.text: f"{colors.get('value').lower()}" for colors in BeautifulSoup(colors, features="html5lib").find_all("option")}
            
            if couleur in colors:
                player.stat[10] = int(colors[couleur], 16)
                await ctx.send(f"La couleur de __{player.name}__ est devenue : {couleur}.")
            else:
                await send_error(ctx, f"couleur inconnue : '{couleur}'. Pour avoir la liste des couleurs disponible : http://www.proftnj.com/RGB3.htm")

        self.save_game()


    @commands.command(help="Changer de lieu.", brief="Changer de lieu")
    @commands.check(server_id)
    @commands.check(awareness)
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
            await send_error(ctx, "vous n'êtes pas un joueur enregistré ou le joueur dont vous voulez voir les statististiques n'existe pas")
            return
    
        # Embed's construction
        info = joueur.get_stat()
        embed = discord.Embed(title=f"{info[0]}", description=f"[{info[19]}]\nStatistiques de {info[0]}, {info[1]}\n de niveau {info[2]}", color=info[13])
        if info[17]: embed.set_thumbnail(url=info[17])
        
        # Capacities
        capacities = ""
        for index, capacity_name in enumerate(("Courage ..", "Force ....", "Habileté .", "Rapidité .", "Intellect ", "Défense ..")):
            capacities += f"`{capacity_name}.: {info[3 + index]}`\n"

        # Misceleanous
        misc = ""
        for index, misc_name in enumerate((f"Vie ...#/{joueur.get_max_health()} PV", "Mana ..#", "Argent # Drachmes", f"Poids .#/{joueur.get_max_weight()}")):
            before, after = misc_name.split("#")
            misc += f"`{before}.: {info[index + 9]}{after}`\n"

        # Inventory
        if info[15]:
            inventory = ""
            for item in info[15]:
                inventory += f" ❖ {item[0]} {('', f' ({item[1]})')[item[1] > 1]}\n"
        else:
            inventory = "< vide >"

        # Powers
        if info[18]:
            powers = ""
            for i in info[18]:
                powers += f" ❖ {i.capitalize()}\n"
        else:
            powers = "< aucun >"

        # Notes
        if info[16][0][0]:
            note = "\n".join([f"{i[0]} - {i[1]}" for i in info[16]])
        else:
            note = "< aucune >"

        # Compétences
        if info[20]:
            abilities = ""
            for i in info[20]: abilities += f" ❖ {i[0].capitalize()} ({i[1]} / 20)\n"
        else:
            abilities = "< aucune >"

        embed.add_field(name="Capacités", value=capacities, inline=True)
        embed.add_field(name="Divers", value=misc, inline=True)
        embed.add_field(name="Lieu", value=info[14], inline=True)
        embed.add_field(name="Inventaire", value=inventory, inline=True)
        embed.add_field(name="Pouvoirs", value=powers, inline=True)
        embed.add_field(name="Compétences", value=abilities, inline=True)
        embed.add_field(name="Notes", value=note, inline=True)

        await ctx.send(embed=embed)


    @commands.command(help="Permet de gérer ses notes.\n\n`contenu` peut être soit une chaîne de caractères si l'on veux ajouter une note, soit l'indice de la note que l'on veut supprimer.", brief="Gérer ses notes")
    @commands.check(server_id)
    async def note(self, ctx, contenu):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        try:
            contenu = int(contenu)
        except:
            pass

        if type(contenu) == str:
            player.add_note(contenu)
            await ctx.send(f"__{player.name}__ a ajouté la note :\n> {contenu}")

        elif type(contenu) == int and contenu > 0:
            check = player.del_note(contenu)
            if check:
                await ctx.send(f"__{player.name}__ a supprimé la note :\n> {check}")
            else:
                await ctx.send(f"*Erreur : la note n°{contenu} n'existe pas.*")

        self.save_game()


    @commands.command(help="Voir la liste des joueurs enregistrés", brief="Voir les joueurs enregistrés")
    @commands.check(server_id)
    async def liste(self, ctx):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return
        color = player.stat[10]

        fields = []
        for player_id in self.data_player:
            player = self.data_player[player_id]
            fields.append((f"{player.name}{('', ' (PnJ)')[player.id <= 0]}", f"{player.species} de niveau {player.get_level()} vers {player.place}\n[{player.get_state()}]"))

        for embed in make_embed(fields, "Joueurs", "Liste des joueurs enregistrés", color):
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
    @commands.check(awareness)
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
    @commands.check(awareness)
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
    @commands.check(awareness)
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
            if player.stat[8] >= nombre:
                player.stat[8] -= nombre
                target.stat[8] += nombre
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


    @commands.command(help="Effectue un lancer de dé dans dans une capacité ou une compétence.", brief="Effectuer un lancer dans une capacité")
    @commands.check(server_id)
    @commands.check(awareness)
    async def lancer(self, ctx, capacite: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        capacities = ("Courage", "Force", "Habileté", "Rapidité", "Intelligence", "Défense")
        capacite = capacite.capitalize()

        if not capacite in capacities:
            capacite = capacite.lower()
            check = player.have_abilities(capacite)
            die_score = randint(1, 20)

            if check != -1: die_score += player.abilities[check][1] // 5

            if die_score > 15:
                player.add_abilities(capacite, check)
                if check == -1:
                    await ctx.send(f"__{player.name}__ a gagné la compétence : '{capacite}'.")
                else:
                    await ctx.send(f"__{player.name}__ a fait un succès critique sur son lancer de compétence : '{capacite}'")

            elif check == -1:
                await ctx.send(f"__{player.name}__ n'a pas réussi à apprendre la compétence : '{capacite}'.")

            elif die_score >= 10 :
                await ctx.send(f"__{player.name}__ a fait un succès sur son lancer de compétence : '{capacite}'.")

            elif die_score > 5:
                await ctx.send(f"__{player.name}__ a fait un échec sur son lancer de compétence : '{capacite}'.")

            else:
                if player.sub_abilities(capacite) == 1:
                    await ctx.send(f"__{player.name}__ a perdu la compétence : '{capacite}'.")
                else:
                    await ctx.send(f"__{player.name}__ a fait un échec critique sur son lancer de compétence : '{capacite}'.")

            self.save_game()

        else:
            index = capacities.index(capacite)
            comment = ("échec critique", "échec", "succès", "succès critique")[player.capacity_roll(index)]
            await ctx.send(f"__{player.name}__ a fait un {comment} sur son lancer " + ("de ", "d'")[index in (2, 4)] + capacities[index])

    
    @commands.command(help="Utiliser ou consulter ses pouvoirs. Le premier argument est le nom du pouvoir à utiliser, le second correspond au nom de l'adversaire visé (dans le cas où le pouvoir utilisé requiert un adversaire).\n\n Si vous laissez ses deux argments vide, vous obtenez la liste de vos pouvoirs avec une description.", brief="Utiliser ou consulter ses pouvoirs")
    @commands.check(server_id)
    @commands.check(awareness)
    async def pouvoir(self, ctx, nom: str=None, adversaire: str=None):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if adversaire:
            name = adversaire
            adversaire = self.get_player_from_name(adversaire)
            if not adversaire: await send_error(ctx, f"{name} n'est pas un joueur enregistré"); return

        if nom:
            power = get_power_by_name(nom.lower())
            nom = nom.capitalize()

            if not power:
                await send_error(ctx, f"le pouvoir '{nom}' n'existe pas")
                return

            if power.power_id not in [i.power_id for i in player.power]:
                await send_error(ctx, f"__{player.name}__ ne possède pas le pouvoir : '{nom}'")
                return

            if player.stat[7] <= 0:
                await ctx.send(f"__{player.name}__ tente d'utiliser {nom}, mais échoue.")
                return

            if power.enemy and not adversaire:
                await send_error(ctx, f"le sort '{nom}' nécessite une cible")
                return

            player.stat[7] -= 1
            await ctx.send(f"__{player.name}__ utilise {nom} :\n" + power_use(power.power_id)(player, self.data_player, adversaire))

        else:   
            fields = []
            for power in player.power:
                description = power.description + ("", " (cible requise)")[power.enemy]
                fields.append((power.name.capitalize(), description))
            
            for embed in make_embed(fields, f"Pouvoirs de {player.name}", "Pouvoirs spéciaux connus et descriptions", player.stat[10]):
                await ctx.send(embed=embed)


    @commands.command(help="Vous permer d'apprendre de nouveau sort. le nom du sort est obligatoire.", brief="Apprend un nouveau pouvoir spécial")
    @commands.check(server_id)
    @commands.check(awareness)
    async def apprend(self, ctx, nom: str):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        check = player.power_add(nom.lower())
        nom = nom.capitalize()

        if check == 0:
            await send_error(ctx, f"le pouvoir '{nom} n'existe pas")
        elif check == 1:
            await send_error(ctx, f"__{player.name}__ a déjà le pouvoir : '{nom}' ou vous avez trop de pouvoirs")
        else:
            await ctx.send(f"__{player.name}__ apprend le pouvoir : '{nom}'.")

        self.save_game()


    @commands.command(help="Vous permer d'oublier un sort. le nom du sort est obligatoire.", brief="Oublier un pouvoir spécial")
    @commands.check(server_id)
    @commands.check(awareness)
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
        if not nom and shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        if nom:
            check, obj = player.have(nom)
            if check == -1:
                obj = get_object(get_official_name(nom, shop_id))
                if shop_id == -1: await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}'"); return
                if obj.shop_id == -1: await send_error(ctx, f"cet objet : '{nom}' n'est pas vendu ici"); return 

            if obj.shop_id == -1: shop = "Cet objet n'est rattaché à aucun magasin"
            else: shop = f"Magasin de rattachement : {get_shop_name()[obj.shop_id][0]}"
            embed = discord.Embed(title=nom, description=f"{shop}", color=player.stat[10])

            capacity = ""
            for index, name in enumerate(("Courage ..", "Force ....", "Habileté .", "Rapidité .", "Intellect ", "Défense ..")):
                capacity += f"`{name}.: {obj.stat[index]}`\n"

            misc = ""
            for index, name in enumerate(("Usage .", "Vie ...# PV", "Mana ..#", "Valeur # Drachmes", "Poids .#")):
                if not index:
                    misc += f"`{name}.: {get_type_by_id(obj.object_type)}`\n"
                else:
                    name = name.split("#")
                    misc += f"`{name[0]}.: {obj.stat[index + 5]}{name[1]}`\n"

            embed.add_field(name="Caractéristiques", value=capacity)
            embed.add_field(name="Divers", value=misc)

            await ctx.send(embed=embed)

        else:
            all_objects = get_object_by_shop(shop_id)
            capacities = ("Courage", "Force", "Habileté", "Rapidité", "Intelligence", "Défense", "Vie", "Mana", "Valeur", "Poids")
                        
            fields = []
            for obj in all_objects:
                capacity = "; ".join([f"{name} : {obj.stat[index]}" for index, name in enumerate(capacities) if obj.stat[index]])
                fields.append((obj.name.capitalize(), capacity))

            for embed in make_embed(fields, player.place, "Liste des articles disponible", player.stat[10]):
                await ctx.send(embed=embed)


    @commands.command(help="Vous permer d'acheter des objets. Le premier paramètre est le nom de l'objet, le second, faculatatif, est le nombre d'objet à acheter.", brief="Acheter un objet")
    @commands.check(server_id)
    @commands.check(awareness)
    async def achat(self, ctx, nom: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        obj = get_official_name(nom.lower())
        obj = get_object(obj, shop_id)
        if obj.shop_id == -1: await send_error(ctx, f"l'objet : '{nom}' n'est pas vendu ici"); return

        if obj.object_type not in (1, 5, 8) or nombre < 1: nombre = 1

        if player.stat[8] >= nombre * obj.stat[8]:
            check = player.object_add(nom, nombre)

            if check:
                player.stat[8] -= nombre * obj.stat[8]
                nb = ("", f" ({nombre})")[nombre > 1]
                await ctx.send(f"__{player.name}__ a acheté l'objet : '{nom}{nb}' pour {nombre * obj.stat[8]} Drachmes.")
            else:
                await send_error(ctx, f"__{player.name}__ a déjà cet objet : '{nom}'")

        else:
            await send_error(ctx, f"__{player.name}__ n'a pas assez de Drachmes pour acheter cet objet : '{nom}'")

        self.save_game()


    @commands.command(help="Permet de vendre un objet. Le nom est à préciser, le nombre d'unité à vendre est facultatif (1 par défaut)", brief="Vendre un objet")
    @commands.check(server_id)
    @commands.check(awareness)
    async def vend(self, ctx, nom: str, nombre: int=1):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        obj = get_object(get_official_name(nom.lower()), shop_id)
        if obj.shop_id == -1: await send_error(ctx, f"l'objet : '{nom}' n'intéresse personne ici"); return

        if obj.object_type not in (1, 5, 8) or nombre < 1: nombre = 1

        check = player.object_del(nom, nombre)

        if check:
            cost = (3 * nombre * obj.stat[8]) // 4
            nombre = ("", f" ({nombre})")[nombre > 1]
            player.stat[8] += cost
            await ctx.send(f"__{player.name}__ a vendu l'objet : '{nom}{nombre}' pour {cost} Drachmes.")
        else:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}', ou pas en assez grande quantité")

        self.save_game()


    @commands.command(help=f"Calculer la vitesse nécessaire pour parcourir une certaine distance.\n\n__Moyens de transport__ : {get_all_travel_mean()}\n\n__Météo__ : {get_all_weather()}\n\n__Terrains__ : {get_all_landtype()}", brief="Calculer un temps de trajet")
    @commands.check(server_id)
    async def temps(self, ctx, distance: int, moyen_transport: str, meteo: str, terrain: str=None):
        
        per_hour, per_day, on_sea = get_travel_mean(moyen_transport)
        weather = get_weather(meteo)[on_sea]

        if -1 in (per_hour, per_day, on_sea):
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
            terrain = get_landtype(terrain)
            if not terrain: await send_error(ctx, "terrain inconnu"); return

            embed = discord.Embed(title="Temps", description=f"Temps nécessaire pour parcourir {distance} km", color=8421504)
            land_name = ("Sur une route", "Sur un chemin", "Hors piste")

            for index, land_type in enumerate(terrain):
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

        names = requests.get(f"https://www.nomsdefantasy.com/{categorie}/short").text
        names = [names.contents[0] for names in BeautifulSoup(names, features="html5lib").find_all("li")]
        
        embed = discord.Embed(title="Générateur de nom", description=f"Nom{('', 's')[nombre > 1]} '{categorie}' au hasard", color=player.stat[10])
        embed.add_field(name="Noms", value=" ❖ " + "\n ❖ ".join(names[:nombre]))
        await ctx.send(embed=embed)


    @commands.command(help="Commencer ou continuer un combat. Précisez le nom de l'adversaire et l'arme utilisée.", brief="Combattre")
    @commands.check(server_id)
    @commands.check(awareness)
    async def combat(self, ctx, adversaire: str, arme: str=None):
        player = self.get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        # Verification de l'existence de la cible, et création d'icelle dans le cas échéant
        target = self.get_player_from_name(adversaire)

        if not target:
            new_player_id = min(self.data_player.keys()) - 1
            if new_player_id > 0: new_player_id = -1
            level = get_avg_level(self.data_player)

            stat = stat_gen([1 for _ in range(5)], randint(1, int(1.5 * level)), True)
            self.data_player.update({new_player_id : Player(new_player_id, adversaire, "Ennemi", "", stat, player.place)})
            self.save_game()

            await ctx.send(f"__{player.name}__ se prépare à combattre __{adversaire}__.")
            return

        # Vérification de l'arme du joueur
        if arme:
            player_weapon, check = weapon_check(player, target, arme)
            if check == 1: await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{arme}'"); return
            elif check == 2: await send_error(ctx, f"__{player.name}__ et __{target.name}__ ne sont pas au même endroit"); return
            elif check == 3: await send_error(ctx, f"__{player.name} n'a pas de projectile pour tirer"); return

        # Si aucune arme n'a été précisée
        elif target.place != player.place:
                await send_error(ctx, f"__{player.name}__ et __{target.name}__ ne sont pas au même endroit")
                return
        else:
            player_weapon = Object("ses mains", "ses mains", [int(i == 8) for i in range(9)], -1, -1)

        # Arme de l'adversaire
        target_can_fight, target_weapon = weapon_select(target)
        if target_weapon.object_type != 4 and target.place != player.place: target_can_fight = False

        # Affichage des statistiques et des modificateurs
        capacities = list(get_capacities()[:6])
        capacities.insert(0, "Capacités")

        max_lgth = len(capacities[0])

        player_capacities = [player.name]
        player_max_lgth = len(player.name)

        target_capacities = [target.name]
        target_max_lgth = len(target.name)

        pml, tml = 0, 0
        for i in range(len(capacities)):
            pml = max(pml, len(str(player.stat[i])))
            tml = max(tml, len(str(target.stat[i])))

        for index in range(len(capacities)):
            max_lgth = max(len(capacities[index]), max_lgth)

            player_capacities.append(f"{player.stat[index]}{' ' * (pml - len(str(player.stat[index])))} [{('', '+')[player_weapon.stat[index] >= 0]}{player_weapon.stat[index]}]")
            player_max_lgth = max(len(player_capacities[-1]), player_max_lgth)

            target_capacities.append(f"{target.stat[index]}{' ' * (tml - len(str(target.stat[index])))} [{('', '+')[target_weapon.stat[index] >= 0]}{target_weapon.stat[index]}]")
            target_max_lgth = max(len(target_capacities[-1]), target_max_lgth)

        message = f"```\n"
        
        for index, name in enumerate(capacities):
            message += f"{name.capitalize() + ' ' * (max_lgth - len(name))} | {player_capacities[index] + ' ' * (player_max_lgth - len(player_capacities[index]))} | {target_capacities[index] + ' ' * (target_max_lgth - len(target_capacities[index]))}\n"

        message += "```\n"

        player.stat_add(player_weapon.stat)
        target.stat_add(target_weapon.stat)

        # Qui commence
        fighters, target_index = phase_1(player, target)

        for attacker in range(2):
            defender = (attacker + 1) % 2

            turn = True
            if attacker == target_index and not target_can_fight:
                message += f"__{fighters[target_index].name}__ ne peut pas se battre.\n"
                turn = False

            end = False
            if turn:
                message += f"__{fighters[attacker].name}__ attaque"
                if attacker == target_index: message += f" avec {target_weapon.name}"
                else: message += f" avec {player_weapon.name}"

                if phase_2(fighters[attacker]):
                    message += " et touche sa cible.\n"

                    damage = phase_3(fighters, attacker, defender)
                    if damage:
                        if fighters[defender].stat[6] < 100 + (fighters[defender].get_level() - 1) * 25: fighters[defender].state = 3
                        message += f"__{fighters[defender].name}__ subit {damage} point{('', 's')[damage > 1]} de dégâts.\n"
                    else:
                        message += f"La défense de __{fighters[defender].name}__ encaisse les dégats.\n"

                    if not fighters[defender].isalive():
                        loot = f"__{fighters[defender].name}__ est mort, __{fighters[attacker].name}__ fouille le cadavre et trouve :\n"
                        
                        if fighters[defender].stat[8]:
                            loot += f" ❖ {fighters[defender].stat[8]} Drachme{('', 's')[fighters[defender].stat[8] > 1]}\n"
                            fighters[attacker].stat[8] += fighters[defender].stat[8]
                        
                        for obj in fighters[defender].inventory:
                            check = fighters[attacker].object_add(obj.name, obj.quantity)
                            if check: loot += f" ❖ {obj.name}{('', f' ({obj.quantity})')[obj.quantity > 1]}\n"

                        self.data_player.pop(fighters[defender].id)

                        message += loot
                        end = True
                else:
                    message += f" et manque sa cible.\n"

            if end: break

        await ctx.send(message)

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

        lvl = player.get_level()
        max_mana = lvl * 5
        
        # Régénération de la vie
        if player.stat[6] < player.get_max_health():
            if player.state == 0: player.state = 3
            player.stat[6] += 5 * lvl

        # régénération de la mana
        if player.state != 3 and player.stat[7] < 5 + (lvl - 1):
            player.stat[7] += 1 + (lvl // 2)

        # Empoisonné
        if player.state == 1:
            player.stat[6] -= random(0, 5 * lvl)

        # Inconscient, endormi
        if player.state in (2, 4):
            player.state = 0
        
        # Blessé
        if player.state == 3 and player.stat[6] >= player.get_max_health():
            player.state = 0
        

        await ctx.send(f"__{player.name}__ se repose.")


    @commands.command(name="plante", help="Donne des informations sur la plante demandée (source : wikiphyto.org)", brief="Informations sur une plante")
    async def plante(self, ctx, nom: str):
        try: result, check_code = wikiphyto_api(nom)
        except:
            embed = discord.Embed(title=nom, description="Erreur", color=8421504)
            embed.add_field(name="Erreur de formatage", value=f"Votre requête ne correspond pas à une plante ou la page correspondante n'est pas formatée de manière standard. Par conséquent Odyssée ne parvient pas à récupérer et analyser les données souhaitées.\nVous pouvez tout de même obtenir des informations en suivant le lien :\n> http://www.wikiphyto.org/wiki/{nom.replace(' ', '_')}")
            await ctx.send(embed=embed)
            return

        # homonymie
        if check_code == 0:
            embed = discord.Embed(title=nom, description=f"Plusieurs plantes correspondent à la recherche : '{nom}'", color=8421504)
            embed.add_field(name="Essayez un nom de plante suivant", value=" ❖ " + " ❖ ".join(result))
       
        # pas de résultat
        elif check_code == 1:
            embed = discord.Embed(title=nom, description="Erreur", color=8421504)
            embed.add_field(name="Plante non trouvée", value=f"Aucune plante ne correspond à la recherche : '{nom}'")
        
        # succès
        else:
            latin_name, family, description, used_parts, properties, img, url = result
            embed = discord.Embed(title=nom, description=f"Plus d'informations sur :\n> {url}", color=8421504)
            if img: embed.set_image(url=img)
            embed.add_field(name="Description et habitat", value="\n".join(description), inline=True)
            embed.add_field(name="Parties utilisées", value="\n".join(used_parts), inline=True)
            embed.add_field(name="Famille botanique et nom latin", value=f"{family}{latin_name}", inline=True)

            for i in properties:
                if len(i) > 1:
                    if len(i[1]) > 1000: i[1] = i[1][: 1000] + "…"
                    embed.add_field(name=i[0], value=i[1], inline=False)
                else: embed.add_field(name=i[0], value="< aucune >", inline=False)
            
        await ctx.send(embed=embed)

