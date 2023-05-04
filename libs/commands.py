from bs4 import BeautifulSoup
import discord
from discord.ext import commands
import json
import os
import requests

from libs.lib_odyssee import *


data_player, data_kick, guild_id = {}, [], 0
data_admin = {}


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


def save_game(name=""):
    export_save(data_player, data_kick, guild_id, name)


def get_player_from_id(player_id):
    if player_id in data_player:
        return data_player[player_id]
    else:
        return None


def get_id_from_name(player_name):
    player_name = player_name.lower()
    for player_id in data_player:
        if data_player[player_id].name.lower() == player_name:
            return player_id
    return None


def get_player_from_name(player_name):
    player_name = player_name.lower()
    for player_id in data_player:
        if data_player[player_id].name.lower() == player_name:
            return data_player[player_id]
    return None


async def awareness(ctx):
    if ctx.author.id not in data_player:
        await ctx.send(f"{ctx.author.name} n'est pas un joueur enregistré")
        return False

    player = data_player[ctx.author.id]
    if player.state == 2:
        await send_error(ctx, f"__{player.name}__ est inconscient(e).")
        return False
    elif player.state == 4:
        await send_error(ctx, f"__{player.name}__ est endormi(e).")
    return True


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


async def is_admin(ctx):
    if str(ctx.guild.id) in data_admin and ctx.author.id in data_admin[str(ctx.guild.id)]:
        return True
    else:
        await send_error(ctx, "commande non-autorisée")
        return False


class OdysseeCommands(commands.Cog):
    def __init__(self, config, savefile, bot):
        global data_player, data_kick, guild_id
        self.data_player, self.data_kick, guild_id = savefile
        self.PREFIX = config["PREFIX"]

        data_player = self.data_player
        data_kick = self.data_kick


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

    @commands.command(help=f"Votre espèce est à préciser impérativement. Si aucun pseudonyme n'est précisé, Odyssée prendra votre nom d'utilisateur.\n__Liste des espèces connues :__ {get_all_species()}", brief="Créer un nouveau joueur")
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

        save_game()

    @commands.command(help="Vous permet de mettre à jour votre avatar dans les fichiers du bot si vous en changez.", brief="Mettre à jour son avatar")
    @commands.check(server_id)
    async def avatar(self, ctx, url: str=None):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if not url: player.avatar = str(ctx.author.avatar.url)
        else: player.avatar = url
        await ctx.send(f"L'avatar de __{player.name}__ a été mis à jour.")
        save_game()


    @commands.command(help="Permet de changer son pseudo dans le jeu. Le pseudo utilisé avec Odyssée n'a aucun rapport avec celui du serveur Discord.", brief="Changer de pseudo")
    @commands.check(server_id)
    async def pseudo(self, ctx, nom: str=None):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if not nom:
            if ctx.author.nick: nom = ctx.author.nick
            else: nom = ctx.author.name
            await ctx.send(f"__{player.name}__ s'appelle désormais : {nom}")
            player.name = nom
        
        elif not get_player_from_name(nom):
            await ctx.send(f"__{player.name}__ s'appelle désormais : {nom}")
            player.name = nom
        
        else:
            await send_error(ctx, "ce pseudo est déjà pris")

        save_game()


    @commands.command(help="Changer sa couleur. En format de couleur, vous pouvez donner le code RVB en hexadécimal ou entrer le nom de la couleur voulue (voir les noms sur le site : http://www.proftnj.com/RGB3.htm).", brief="Changer sa couleur")
    @commands.check(server_id)
    async def couleur(self, ctx, couleur: str):
        player = get_player_from_id(ctx.author.id)
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

        save_game()


    @commands.command(help="Changer de lieu.", brief="Changer de lieu")
    @commands.check(server_id)
    @commands.check(awareness)
    async def lieu(self, ctx, lieu: str):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        player.place = lieu
        await ctx.send(f"__{player.name}__ se dirige vers {lieu}.")

        save_game()


    @commands.command(help="Voir ses statistiques, spécifier un nom de joueur permet de voir les statististiques du joueur ciblé.", brief="Voir ses statistiques")
    @commands.check(server_id)
    async def stat(self, ctx, joueur: str=None):
        if joueur: joueur = get_player_from_name(joueur)
        else: joueur = get_player_from_id(ctx.author.id)

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
        player = get_player_from_id(ctx.author.id)
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

        save_game()


    @commands.command(help="Voir la liste des joueurs enregistrés", brief="Voir les joueurs enregistrés")
    @commands.check(server_id)
    async def liste(self, ctx):
        player = get_player_from_id(ctx.author.id)
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
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if nombre <= 0: nombre = 1
        check = player.object_add(*player.have(nom), nombre, nom)
        
        if not check in (0, 3):
            if check == 1: nombre = f" ({nombre})"
            else: nombre = ""
            await ctx.send(f"__{player.name}__ prend {nom}{nombre}")
        else:
            await send_error(ctx, f"__{player.name}__ ne peut pas prendre l'objet : '{nom}' (objet non préhensible ou déjà possédé)")

        save_game()


    @commands.command(help="Jetter un objet, le premier paramètre est le nom de l'objet à jeter, le second est optionnel et correspond au nombre d'objets à jeter.", brief="Jeter un objet")
    @commands.check(server_id)
    @commands.check(awareness)
    async def jette(self, ctx, nom: str, nombre: int=1):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if nombre <= 0: nombre = 1
        check = player.object_del(*player.have(nom), nombre)

        if check == 1:
            if nombre > 1: nombre = f" ({nombre})"
            else: nombre = ""
            await ctx.send(f"__{player.name}__ jette {nom}{nombre}")
        else:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}', ou pas en assez grande quantité")

        save_game()


    @commands.command(help="Sert à utiliser un objet (manger de la nourriture ou consommer un bien). Le premier argument est le nom de l'objet à utiliser, le second (optionnel) correspond au nombre d'unité à utiliser.", brief="Utiliser un objet")
    @commands.check(server_id)
    @commands.check(awareness)
    async def utilise(self, ctx, nom: str, nombre: int=1):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if nombre <= 0: nombre = 1
        check = player.object_use(nom, nombre)

        if check == 1:
            await ctx.send(f"__{player.name}__ utilise {nom} ({nombre}).")
        elif check == 2:
            await send_error(ctx, f"__{player.name}__ ne peut pas utiliser cet objet : '{nom}'")
        else:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}', ou pas en assez grande qantité")

        save_game()


    @commands.command(help="Donner un objet à un joueur. Le premier argument est le nom du joueur, le second le nom de l'objet ('Argent', ou 'Drachmes' pour donner de l'argent). Le dernier paramètre, faculatatif correspond à la quantité donnée (nombre d'unité ou montant).", brief="Donner un objet")
    @commands.check(server_id)
    @commands.check(awareness)
    async def donne(self, ctx, joueur: str, objet: str, nombre: int=1):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        target = get_player_from_name(joueur)
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
            check_player = player.object_del(*player.have(object_name), nombre)
            check_target = target.object_add(*target.have(object_name), nombre, object_name)
            is_ok = True

            if not check_player:
                await send_error(ctx, f"__{player.name}__ ne possède pas cet objet : '{objet}' ou pas en assez grande quantité")
                if check_target: target.object_del(*target.have(object_name), nombre, True)
                is_ok = False

            if not check_target:
                await send_error(ctx, f"__{target.name}__ a déjà cet objet : '{objet}'")
                if check_player: player.object_add(*player.have(object_name), nombre, object_name)
                is_ok = False

            if is_ok:
                nombre = ("", f" ({nombre})")[nombre > 1]
                await ctx.send(f"__{player.name}__ a donné {objet}{nombre} à __{target.name}__.")

        save_game()


    @commands.command(name="dé", help="Lancer un dé. Le premier paramètre est le nombre de dés lancés, le second est le nombre de faces du ou des dés lancés (> 3). Les deux paramètres sont optionnels, par défault, un dé à 20 faces est lancé.", brief="Lancer un dé")
    @commands.check(server_id)
    async def de(self, ctx, nombre: int=1, faces: int=20):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if faces < 4: faces = 4
        if nombre < 1: nombre = 1
        result = randint(nombre, nombre * faces)

        await ctx.send(f"__{player.name}__ lance {nombre} dé{('', 's')[nombre > 1]} à {faces} faces : {result} / {nombre * faces}.")


    @commands.command(help=f"Effectue un lancer de dé dans dans une capacité ou une compétence.\n\n__Capacités connues :__ {', '.join(get_capacities()[: 6])}", brief="Effectuer un lancer dans une capacité")
    @commands.check(server_id)
    @commands.check(awareness)
    async def lancer(self, ctx, capacite: str):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        capacities = [i.capitalize() for i in get_capacities()[: 6]]
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
                if player.sub_abilities(capacite, check) == 1:
                    await ctx.send(f"__{player.name}__ a perdu la compétence : '{capacite}'.")
                else:
                    await ctx.send(f"__{player.name}__ a fait un échec critique sur son lancer de compétence : '{capacite}'.")

            save_game()

        else:
            index = capacities.index(capacite)
            comment = ("échec critique", "échec", "succès", "succès critique")[player.capacity_roll(index)]
            await ctx.send(f"__{player.name}__ a fait un {comment} sur son lancer " + ("de ", "d'")[index in (2, 4)] + capacities[index] + ".")

    
    @commands.command(help="Utiliser ou consulter ses pouvoirs. Le premier argument est le nom du pouvoir à utiliser, le second correspond au nom de l'adversaire visé (dans le cas où le pouvoir utilisé requiert un adversaire).\n\n Si vous laissez ses deux argments vide, vous obtenez la liste de vos pouvoirs avec une description.", brief="Utiliser ou consulter ses pouvoirs")
    @commands.check(server_id)
    @commands.check(awareness)
    async def pouvoir(self, ctx, nom: str=None, adversaire: str=None):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        if adversaire:
            name = adversaire
            adversaire = get_player_from_name(adversaire)
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

            if player.stat[7] < power.mana_cost:
                await ctx.send(f"__{player.name}__ tente d'utiliser {nom}, mais échoue.")
                return

            if power.enemy and not adversaire:
                await send_error(ctx, f"le sort '{nom}' nécessite une cible")
                return

            player.stat_sub(player.stat_modifier)
            player.stat[7] -= power.mana_cost
            await ctx.send(f"__{player.name}__ utilise {nom} :\n" + power_use(power.power_id)(player, self.data_player, adversaire))
            player.stat_add(player.stat_modifier)


        else:   
            fields = []
            for power in player.power:
                description = f"{power.description} (coût en Mana : {power.mana_cost})" + ("", " (cible requise)")[power.enemy]
                fields.append((power.name.capitalize(), description))
            
            for embed in make_embed(fields, f"Pouvoirs de {player.name}", "Pouvoirs spéciaux connus et descriptions", player.stat[10]):
                await ctx.send(embed=embed)

        save_game()


    @commands.command(help="Vous permer d'apprendre de nouveau sort. le nom du sort est obligatoire.", brief="Apprend un nouveau pouvoir spécial")
    @commands.check(server_id)
    @commands.check(awareness)
    async def apprend(self, ctx, nom: str):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        check = player.power_add(nom.lower())
        nom = nom.capitalize()

        if check == 0:
            await send_error(ctx, f"le pouvoir '{nom}' n'existe pas")
        elif check == 1:
            await send_error(ctx, f"__{player.name}__ a déjà le pouvoir : '{nom}' ou vous avez trop de pouvoirs")
        else:
            await ctx.send(f"__{player.name}__ apprend le pouvoir : '{nom}'.")

        save_game()


    @commands.command(help="Vous permer d'oublier un sort. le nom du sort est obligatoire.", brief="Oublier un pouvoir spécial")
    @commands.check(server_id)
    @commands.check(awareness)
    async def oublie(self, ctx, nom: str):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        check = player.power_sub(nom.lower())
        nom = nom.capitalize()

        if check == 0:
            await send_error(ctx, f"le pouvoir '{nom} n'existe pas")
        elif check == 1:
            await send_error(ctx, f"__{player.name}__ n'a pas le pouvoir : '{nom}'")
        else:
            await ctx.send(f"__{player.name}__ oublie le pouvoir : '{nom}'.")

        save_game()


    @commands.command(help="Vous permet de consulter la liste des articles disponible. Préciser un nom vous renvoie la description détaillée de l'objet demandé.", brief="Voir les articles disponibles")
    @commands.check(server_id)
    async def article(self, ctx, nom: str=None):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if not nom and shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        if nom:
            check, obj = player.have(nom)
            if check == -1:
                obj = get_object(get_official_name(nom, shop_id))
                if shop_id == -1: await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}'"); return
                if obj.shop_id == -1: await send_error(ctx, f"l'objet : '{nom}' n'est pas vendu ici"); return 

            if obj.shop_id == -1: shop = "Cet objet n'est rattaché à aucun magasin"
            else: shop = f"Magasin de rattachement : {get_shop_name()[obj.shop_id][0]}"
            embed = discord.Embed(title=nom, description=f"{shop}", color=player.stat[10])

            capacity = ""
            for index, name in enumerate(("Courage ..", "Force ....", "Habileté .", "Rapidité .", "Intellect ", "Défense ..")):
                capacity += f"`{name}.: {obj.stat[index]}`\n"

            misc = ""
            for index, name in enumerate(("Type ..", "Vie ...# PV", "Mana ..#", "Valeur # Drachmes", "Poids .#")):
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
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        obj = get_official_name(nom.lower())
        obj = get_object(obj, shop_id)
        if obj.shop_id == -1: await send_error(ctx, f"l'objet : '{nom}' n'est pas vendu ici"); return

        if obj.object_type not in (1, 5, 8) or nombre < 1: nombre = 1

        if player.stat[8] >= nombre * obj.stat[8]:
            check = player.object_add(*player.have(nom), nombre, nom)

            if check:
                player.stat[8] -= nombre * obj.stat[8]
                nb = ("", f" ({nombre})")[nombre > 1]
                await ctx.send(f"__{player.name}__ a acheté l'objet : '{nom}{nb}' pour {nombre * obj.stat[8]} Drachmes.")
            else:
                await send_error(ctx, f"__{player.name}__ a déjà cet objet : '{nom}'")

        else:
            await send_error(ctx, f"__{player.name}__ n'a pas assez de Drachmes pour acheter cet objet : '{nom}'")

        save_game()


    @commands.command(help="Permet de vendre un objet. Le nom est à préciser, le nombre d'unité à vendre est facultatif (1 par défaut)", brief="Vendre un objet")
    @commands.check(server_id)
    @commands.check(awareness)
    async def vend(self, ctx, nom: str, nombre: int=1):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        shop_id = player.in_shop()
        if shop_id == -1: await send_error(ctx, f"__{player.name}__ n'est pas dans un magasin"); return

        check, obj = player.have(nom)
        
        if obj.shop_id != shop_id: await send_error(ctx, f"l'objet : '{nom}' n'intéresse personne ici"); return
        if obj.object_type not in (1, 5, 8) or nombre < 1: nombre = 1

        check = player.object_del(check, obj, nombre)

        if check:
            cost = nombre * (3 * obj.stat[8] // 4) 
            nombre = ("", f" ({nombre})")[nombre > 1]
            player.stat[8] += cost
            await ctx.send(f"__{player.name}__ a vendu l'objet : '{nom}{nombre}' pour {cost} Drachmes.")
        else:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{nom}', ou pas en assez grande quantité")

        save_game()

    @commands.command(help="Vous permet de vous reposer lorsque vous dormez dehors.", brief="Dormir")
    @commands.check(server_id)
    async def dormir(self, ctx):
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        places = [player.place for player in self.data_player.values() if player.id < 0]
        if player.place in places:
            await send_error(ctx, f"__{player.name}__ ne peut pas dormir : il y a des ennemis potentiels à proximité")
            return

        player.sleep()

        await ctx.send(f"__{player.name}__ se repose.")
        save_game()

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
        player = get_player_from_id(ctx.author.id)
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
        player = get_player_from_id(ctx.author.id)
        if not player: await send_error(ctx, f"{ctx.author.name} n'est pas un joueur enregistré"); return

        # Verification de l'existence de la cible, et création d'icelle dans le cas échéant
        target = get_player_from_name(adversaire)

        if not target:
            new_player_id = min(self.data_player.keys()) - 1
            if new_player_id > 0: new_player_id = -1
            level = get_avg_level(self.data_player)

            stat = stat_gen([1 for _ in range(5)], randint(1, int(1.5 * level)), True)
            self.data_player.update({new_player_id : Player(new_player_id, adversaire, "Ennemi", "", stat, player.place)})
            save_game()

            await ctx.send(f"__{player.name}__ se prépare à combattre __{adversaire}__.")
            return
        else:
            if target.state == 6:
                await ctx.send("__{player.name}__ ne peut pas attaquer __{target.name}__ car ce dernier est invisible.")
                return

        message = await fight_main(player, target, arme, self.data_player, ctx)
        await ctx.send(message)
        save_game()

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


class AdminCommands(commands.Cog):
    def __init__(self, config, savefile, bot):
        global data_admin
        self.data_player, self.data_kick = data_player, data_kick
        
        self.PREFIX = config["PREFIX"]
        data_admin = config["ADMIN"]

        self.bot = bot

    @commands.command(help="Affiche la documentation sur les fonctions d'administration.", brief="Afficher ce panneau")
    @commands.check(is_admin)
    async def aide_admin(self, ctx, commande: str=None):

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
            
            for embed in make_embed(fields, f"Rubrique des commandes administrateur", f"Entrez : `{self.PREFIX}aide_admin <commande>` pour plus d'informations."):
                await ctx.send(embed=embed)


    @commands.command(name="joueur+", help="Permet d'ajouter un personnage non jouable au jeu en cours. Préciser l'espèce du joueur et son nom.", brief="Ajouter un PnJ")
    @commands.check(is_admin)
    async def joueur_plus(self, ctx, nom: str, espece: str, niveau: int=0, lieu: str="< inconnu >"):
        if get_id_from_name(nom):
            await send_error(ctx, f"le joueur : '{nom}' existe déjà")
        else:
            if niveau <= 0: niveau = randint(1, get_avg_level(self.data_player) + 2)
            new_player_id = min(self.data_player.keys()) - 1
            if new_player_id > 0: new_player_id = -1
            
            stat = stat_gen([1 for _ in range(5)], niveau, True)

            self.data_player.update({new_player_id : Player(new_player_id, nom, espece, '', stat, lieu)})
            await ctx.send(f"{nom}, un(e) {espece} de niveau {niveau}, est apparu(e).")

            save_game()


    @commands.command(name="joueur-", help="Permet de supprimer un joueur sans le kicker.", brief="Supprimer un joueur")
    @commands.check(is_admin)
    async def joueur_moins(self, ctx, nom: str):
        player_id = get_id_from_name(nom)

        if player_id:
            self.data_player.pop(player_id)
            await ctx.send(f"Le joueur : __{nom}__ a été supprimé.")
            save_game()
        else:
            await send_error(ctx, f"le joueur : '{nom}' n'existe pas")


    @commands.command(help=f"Permet de mofifier chaque caractéristique d'un joueur.\n\n__Caractétistiques connues :__ les capacités ({', '.join(get_capacities())}) et statistiques, l'inventaire, le lieu, les états, les pouvoirs et les compétences.", brief="Modifier un joueur")
    @commands.check(is_admin)
    async def modifier(self, ctx, nom: str, capacite: str, valeur, nombre: int=1):
        player_id = get_id_from_name(nom)
        if not player_id: await send_error(ctx, f"le joueur : '{nom}' n'existe pas"); return

        player = self.data_player[player_id]
        try: valeur = int(valeur)
        except: pass

        capacite = capacite.lower()
        capacities = get_capacities()
        
        if capacite in capacities:
            player.stat[capacities.index(capacite)] += valeur
            if player.state == 0 and player.stat[6] < player.get_max_health(): player.state = 3
            elif player.state == 3 and player.stat[6] >= player.get_max_health(): player.state = 0
            
            if capacite != "argent":
                msg = f"__{player.name}__ {('perd', 'gagne')[valeur > 0]} {abs(valeur)} point{('', 's')[abs(valeur) > 1]} "
                if capacite == "habileté": msg += "d'Habileté"
                elif capacite == "intelligence": msg += "d'Intelligence"
                else: msg += f"de {capacite.capitalize()}."

                if not player.isalive():
                    msg += f"\n__{player.name}__ est mort."
                    self.data_player.pop(player.id)
            else:
                msg = f"__{player.name}__ {('perd', 'gagne')[valeur > 0]} {abs(valeur)} Drachme{('', 's')[abs(valeur) > 1]}."
            
            await ctx.send(msg)

        elif capacite == "lieu":
            player.place = valeur
            await ctx.send(f"__{player.name}__ se dirige vers {valeur}.")

        elif capacite == "objet+":
            check = player.object_add(*player.have(valeur), nombre, valeur)
            nombre = ("", f" ({nombre})")[nombre > 1]
            
            if check: await ctx.send(f"__{player.name}__ récupère l'objet : '{valeur}'{nombre}.")
            else: await send_error(ctx, f"__{player.name}__ a déjà l'objet : '{valeur}'")

        elif capacite == "objet-":
            check = player.object_del(*player.have(valeur), nombre)
            nombre = ("", f" ({nombre})")[nombre > 1]

            if check: await ctx.send(f"__{player.name}__ a perdu l'objet : '{valeur}'{nombre}.")
            else: await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{valeur}' ou pas en assez grande quantité")

        elif capacite == "pouvoir+":
            check = player.power_add(valeur.lower())
            valeur = valeur.capitalize()

            if check == 0:
                await send_error(ctx, f"le pouvoir '{valeur} n'existe pas")
            elif check == 1:
                await send_error(ctx, f"__{player.name}__ a déjà le pouvoir : '{valeur}' ou vous avez trop de pouvoirs")
            else:
                await ctx.send(f"__{player.name}__ apprend le pouvoir : '{valeur}'.")

        elif capacite == "pouvoir-":
            check = player.power_sub(valeur.lower())
            valeur = valeur.capitalize()

            if check == 0:
                await send_error(ctx, f"le pouvoir '{valeur} n'existe pas")
            elif check == 1:
                await send_error(ctx, f"__{player.name}__ n'a pas le pouvoir : '{valeur}'")
            else:
                await ctx.send(f"__{player.name}__ oublie le pouvoir : '{valeur}'.")

        elif capacite == "état":
            valeur = valeur.lower()
            state = get_state_by_name(valeur)

            if state in (5, 6):
                await send_error(ctx, "ce status ne peut pas être affecté manuellement à un joueur")
                return

            if state + 1:
                if player.state == 5:
                    player.stat_sub(player.stat_modifier)
                    player.stat_modifier = [0 for _ in range(8)]
                    player.state = state
                elif player.state == 6:
                    player.state = state
                await ctx.send(f"__{player.name}__ devient {valeur}.")
            else:
                await send_error(ctx, f"{valeur} n'est pas un état connu")

        elif capacite == "compétence+":
            check = player.have_abilities(valeur)
            if player.add_abilities(valeur, check, nombre) == 1:
                await ctx.send(f"__{player.name}__ gagne la compétence : '{valeur}'.")
            else:
                await ctx.send(f"__{player.name}__ gagne {nombre} point{('', 's')[nombre > 1]} sur la compétence : '{valeur}'.")

        elif capacite == "compétence-":
            check = player.have_abilities(valeur)
            if check == -1:
                await send_error(ctx, f"__{player.name}__ ne possède pas la compétence : '{valeur}'")
            else:
                if player.sub_abilities(valeur, check, nombre) == 1:
                    await ctx.send(f"__{player.name}__ a perdu la compétence : '{valeur}'.")
                else:
                    await ctx.send(f"__{player.name}__ a perdu {nombre} point{('', 's')[nombre > 1]} sur la compétence : '{valeur}'.")

        save_game()

    @commands.command(help="Permet de modifier les statistiques d'un objet possédé par un joueur.", brief="Permet de modifier les caractéristique d'une arme")
    @commands.check(is_admin)
    async def modifier_objet(self, ctx, nom: str, objet:str, capacite: str, valeur):
        player_id = get_id_from_name(nom)
        if not player_id: await send_error(ctx, f"le joueur : '{nom}' n'existe pas"); return

        player = self.data_player[player_id]
        index, obj = player.have(objet)
        
        if index == -1:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{objet}'")
        
        else:
            try:
                valeur = int(valeur)
            except:
                pass

            capacities = get_capacities()
            capacite = capacite.lower()

            if capacite in capacities:
                cap_index = capacities.index(capacite)
                player.inventory[index].stat[cap_index] += valeur
                if obj.object_type == 0: player.stat[cap_index] += valeur
                
                if cap_index == 8:
                    await ctx.send(f"L'objet '{objet}' de __{player.name}__ {('perd', 'gagne')[valeur > 0]} {valeur} Drachme{('', 's')[valeur > 1]} de valeur.")
                else:
                    await ctx.send(f"L'objet '{objet}' de __{player.name}__ {('perd', 'gagne')[valeur > 0]} {valeur} point{('', 's')[valeur > 1]} en {capacite.capitalize()}.")
            
            elif capacite == "type":
                new_type = get_type_by_id(valeur)
                if new_type:
                    player.inventory[index].object_type = valeur
                    await ctx.send(f"Le type de l'objet '{objet}' de __{player.name}__ est devenu : '{new_type}'.")
                else:
                    await send_error(ctx, f"{valeur} n'est pas l'indice d'un type connu")

            elif capacite == "magasin":
                shops_name = get_shop_name()
                if 0 <= valeur < len(shops_name):
                    new_shop = get_shop_name()[valeur][0]
                    player.inventory[index].shop_id = valeur
                    await ctx.send(f"Vous pouvez désormais vendre l'objet '{objet}' dans les magasins de type {new_shop}.")
                elif valeur == -1:
                    player.inventory[index].shop_id = valeur
                    await ctx.send(f"Vous ne pouvez plus vendre l'objet '{objet}' dans un magasin.")
                else:
                    await send_error(ctx, f"{valeur} n'est pas un indice de magasin connu")

            elif capacite == "nom":
                check, _ = player.have(valeur)

                if check == -1 or check == index:
                    player.inventory[index].name = valeur
                    await ctx.send(f"L'objet '{objet}' s'appelle désormais '{valeur}'.")
                else:
                    await send_error(ctx, f"'{valeur}' est un autre objet de l'inventaire")

            else:
                await send_error(ctx, f"'{capacite}' n'est pas une capacité connue")

        save_game()

    @commands.command(help="Supprime la totalité de la sauvegarde du jeu en cours.", brief="Supprime la sauvegarde")
    @commands.check(is_admin)
    async def formatage(self, ctx):
        global guild_id
        self.data_player.clear()
        self.data_kick.clear()
        guild_id = 0

        await ctx.send("Partie supprimée.")
        save_game()


    @commands.command(help="Supprime un joueur et l'empêche de créer un nouveau personnage.", brief="Kick un joueur")
    @commands.check(is_admin)
    async def kick(self, ctx, nom: str):
        player_id = get_id_from_name(nom)

        if player_id:
            self.data_player.pop(player_id)
            self.data_kick.append(player_id)
            
            await ctx.send(f"__{nom}__ a été kické.\n`id : {player_id}`")
            save_game()

        else:
            await send_error(ctx, f"le joueur : '{nom}' n'existe pas")


    @commands.command(help="Autorise un joueur kické à revenir. L'id du joueur est à connaître.", brief="Unkick un joueur")
    @commands.check(is_admin)
    async def unkick(self, ctx, id_joueur: int):
        if id_joueur in self.data_kick:
            self.data_kick.remove(id_joueur)
            await ctx.send(f"Le joueur a été unkick.")
            save_game()
        else:
            await send_error(ctx, "ce joueur n'est pas kické")


    @commands.command(help="Charge la sauvegarde donnée en argument. La sauvegarde doit être en fichier joint", brief="Charger une partie")
    @commands.check(server_id)
    @commands.check(is_admin)
    async def charger(self, ctx, nom: str=""):
        global guild_id

        if ctx.message.attachments:
            data = json.loads(await ctx.message.attachments[0].read())
            data_player, data_kick, new_guild_id = data["players"], data["kicks"], data["guild_id"]
        else:
            if not nom: nom = str(ctx.guild.id)
            data_player, data_kick, new_guild_id = search_save(nom)
        
        if new_guild_id and new_guild_id != ctx.guild.id:
            await send_error(ctx, "cette sauvegarde ne vient pas de ce serveur")
            return

        self.data_player.clear()
        guild = self.bot.get_guild(guild_id)
        for player in data_player:
            self.data_player.update({player[0]: Player(*player)})

        self.data_kick.clear()
        for i in data_kick:
            self.data_kick.append(i)

        guild_id = new_guild_id

        await ctx.send("Partie chargée.")
        save_game()


    @commands.command(help="Sauvegarde la partie dans un fichier séparé et renvoie une copie du fichier.", brief="Sauvegarde la partie.")
    @commands.check(is_admin)
    async def sauvegarde(self, ctx, nom: str=""):
        if not nom: nom = str(ctx.guild.id)
        save_game(nom)

        with open(f"saves/save.json", "r") as file:
            await ctx.send(f"**Sauvegarde**", file=discord.File("saves/save.json"))


    @commands.command(help="Permet d'ajouter un objet au jeu. 'magagin' et 'type_objet' sont les id et non les noms.\n\n__Magasins :__\n" + "\n".join([f"{index} - {value[0]}" for index, value in enumerate(get_shop_name())]) + "\n\n__Types :__\n" + "\n".join([f"{index} - {value}" for index, value in get_all_types()]), brief="Ajouter un objet")
    @commands.check(is_admin)
    async def ajout_objet(self, ctx, magasin: int, type_objet: int, nom: str, courage: int, force: int, habilete: int, rapidite: int, intelligence: int, defense: int, vie: int, mana: int, argent: int, poids: int):
        check = get_official_name(nom)
        if check: await send_error(f"l'objet : '{nom}' existe déjà"); return

        table = sqlite3.connect("BDD/odyssee_objects.db")
        c = table.cursor()
        c.execute(f"INSERT INTO objets VALUES ({magasin}, {type_objet}, \"{nom}\", {courage}, {force}, {habilete}, {rapidite}, {intelligence}, {defense}, {vie}, {mana}, {argent}, {poids})")

        table.commit()
        table.close()

        await ctx.send(f"L'objet : '{nom}' a été ajouté à la base de données.")


    @commands.command(help="Un joueur se fait attaquer par un PnJ", brief="Attaquer un joueur")
    @commands.check(is_admin)
    async def pnj_combat(self, ctx, joueur: str, adversaire: str, arme: str=None):
        pnj = get_id_from_name(joueur)
        if not pnj: await send_error(ctx, f"{joueur} n'existe pas") ; return
        pnj = self.data_player[pnj]
        if pnj.id > 0 or pnj.state in (2, 4): await send_error(ctx, f"__{pnj.name}__ n'est pas un PnJ ou n'est pas en état de se battre") ; return

        target = get_id_from_name(adversaire)

        if not target: await send_error(ctx, f"{adversaire} n'est pas un joueur enregistré") ; return
        target = self.data_player[target]

        if target.state == 6:
            await ctx.send(f"__{pnj.name}__ ne peut pas attaquer : __{target.name}__ est invisible.")
            return

        message = await fight_main(pnj, target, arme, self.data_player, ctx)       
        await ctx.send(message)
        save_game()


    @commands.command(help="Fait dormir les joueurs (PnJ compris).", brief="Fait dormir les joueurs.")
    @commands.check(is_admin)
    async def nuit(self, ctx):
        players_names = []
        for player in self.data_player.values():
            places = [i.place for i in self.data_player.values() if i.id * player.id < 0]
            if player.place in places:
                await send_error(ctx, f"__{player.name}__ ne peut pas dormir : il y a des ennemis potentiels à proximité")
            
            else:
                players_names.append(f"__{player.name}__")
                player.sleep()
                
        if len(players_names) == 1:
            await ctx.send(f"__{players_names[0]}__ s'est reposé.")
        elif len(players_names) > 1:
            await ctx.send(f"{', '.join(players_names[:-1])} et {players_names[-1]} se sont reposés.")
        
        save_game()


    @commands.command(help="Permet de faire en sorte qu'un PnJ utilise un de ses pouvoirs", brief="Utiliser un pouvoir d'un PnJ")
    @commands.check(is_admin)
    async def pnj_pouvoir(self, ctx, joueur: str, nom: str=None, adversaire: str=None):
        pnj = get_id_from_name(joueur)
        if not pnj: await send_error(ctx, f"{joueur} n'est pas un joueur enregistré"); return
        pnj = self.data_player[pnj]
        if pnj.id > 0 or pnj.state in (2, 4): await send_error(ctx, f"__{pnj.name}__ n'est pas un PnJ ou n'est pas en état de se battre") ; return


        if adversaire:
            name = adversaire
            adversaire = get_id_from_name(adversaire)
            if not adversaire: await send_error(ctx, f"{name} n'est pas un joueur enregistré"); return
            adversaire = self.data_player[adversaire]

        if nom:
            power = get_power_by_name(nom.lower())
            nom = nom.capitalize()

            if not power:
                await send_error(ctx, f"le pouvoir '{nom}' n'existe pas")
                return

            if power.power_id not in [i.power_id for i in pnj.power]:
                await send_error(ctx, f"__{pnj.name}__ ne possède pas le pouvoir : '{nom}'")
                return

            if pnj.stat[7] <= 0:
                await ctx.send(f"__{pnj.name}__ tente d'utiliser {nom}, mais échoue.")
                return

            if power.enemy and not adversaire:
                await send_error(ctx, f"le sort '{nom}' nécessite une cible")
                return

            pnj.stat[7] -= 1
            await ctx.send(f"__{pnj.name}__ utilise {nom} :\n" + power_use(power.power_id)(pnj, self.data_player, adversaire))

        else:   
            fields = []
            for power in pnj.power:
                description = power.description + ("", " (cible requise)")[power.enemy]
                fields.append((power.name.capitalize(), description))
            
            for embed in make_embed(fields, f"Pouvoirs de {pnj.name}", "Pouvoirs spéciaux connus et descriptions", pnj.stat[10]):
                await ctx.send(embed=embed)

        save_game()

    @commands.command(help=f"Permet à un PnJ de un lancer de dé dans dans une capacité ou une compétence.\n\n__Capacités connues :__ {', '.join(get_capacities()[: 6])}", brief="Effectuer un lancer dans une capacité pour un PnJ")
    @commands.check(server_id)
    @commands.check(awareness)
    async def pnj_lancer(self, ctx, joueur: str, capacite: str):
        pnj = get_id_from_name(joueur)
        if not pnj: await send_error(ctx, f"{joueur} n'est pas un joueur enregistré"); return
        pnj = self.data_player[pnj]
        if pnj.id > 0 or pnj.state in (2, 4): await send_error(ctx, f"__{pnj.name}__ n'est pas un PnJ ou n'est pas en état d'effectuer un lancer'") ; return

        capacities = [i.capitalize() for i in get_capacities()[: 6]]
        capacite = capacite.capitalize()

        if not capacite in capacities:
            capacite = capacite.lower()
            check = pnj.have_abilities(capacite)
            die_score = randint(1, 20)

            if check != -1: die_score += pnj.abilities[check][1] // 5

            if die_score > 15:
                pnj.add_abilities(capacite, check)
                if check == -1:
                    await ctx.send(f"__{pnj.name}__ a gagné la compétence : '{capacite}'.")
                else:
                    await ctx.send(f"__{pnj.name}__ a fait un succès critique sur son lancer de compétence : '{capacite}'")

            elif check == -1:
                await ctx.send(f"__{pnj.name}__ n'a pas réussi à apprendre la compétence : '{capacite}'.")

            elif die_score >= 10 :
                await ctx.send(f"__{pnj.name}__ a fait un succès sur son lancer de compétence : '{capacite}'.")

            elif die_score > 5:
                await ctx.send(f"__{pnj.name}__ a fait un échec sur son lancer de compétence : '{capacite}'.")

            else:
                if pnj.sub_abilities(capacite) == 1:
                    await ctx.send(f"__{pnj.name}__ a perdu la compétence : '{capacite}'.")
                else:
                    await ctx.send(f"__{pnj.name}__ a fait un échec critique sur son lancer de compétence : '{capacite}'.")

            save_game()

        else:
            index = capacities.index(capacite)
            comment = ("échec critique", "échec", "succès", "succès critique")[pnj.capacity_roll(index)]
            await ctx.send(f"__{pnj.name}__ a fait un {comment} sur son lancer " + ("de ", "d'")[index in (2, 4)] + capacities[index] + ".")
