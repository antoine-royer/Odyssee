import discord
from discord.ext import commands

from libs.lib_odyssee import *

guild_id, data_admin = None, []


async def is_admin(ctx):
    if ctx.author.id not in data_admin:
        await send_error(ctx, "commande non-autorisée")
        return False
    return True


class AdminCommands(commands.Cog):
    def __init__(self, config, savefile):
        global guild_id, data_admin
        self.data_player, self.data_kick, guild_id = savefile
        self.PREFIX = config["PREFIX"]
        data_admin = config["ADMIN"]


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
                return player_id
        return None


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
        
        else:
            embed = discord.Embed(title="Rubrique des commandes administrateur", description=f"Entrez : `{self.PREFIX}administration <commande>` pour plus d'informations.", color=8421504)
            for cmnd in self.get_commands():
                embed.add_field(name=cmnd.brief, value=get_syntax(cmnd), inline=False)
        await ctx.send(embed=embed)


    @commands.command(name="joueur+", help="Permet d'ajouter un personnage non jouable au jeu en cours. Préciser l'espèce du joueur et son nom.", brief="Ajouter un PnJ")
    @commands.check(is_admin)
    async def joueur_plus(self, ctx, espece: str, nom: str):

        level = get_avg_level(self.data_player) 

        if self.get_player_from_name(nom):
            await send_error(ctx, f"le joueur : '{nom}' existe déjà")
        else:
            new_player_id = -(len(self.data_player) + 1)
            
            stat = stat_gen([1 for _ in range(4)], randint(1, level + 2), True)

            self.data_player.update({new_player_id : Player(new_player_id, nom, espece, '', stat)})
            await ctx.send(f"{nom}, un(e) {espece}, est apparu(e).")

            self.save_game()


    @commands.command(name="joueur-", help="Permet de supprimer un joueur sans le kicker.", brief="Supprimer un joueur")
    @commands.check(is_admin)
    async def joueur_moins(self, ctx, nom: str):
        player_id = self.get_player_from_name(nom)

        if player_id:
            self.data_player.pop(player_id)
            await ctx.send(f"Le joueur : '{nom}' a été supprimé.")

            self.save_game()
        else:
            await send_error(ctx, f"le joueur : '{nom}' n'existe pas")


    @commands.command(help="Permet de mofifier chaque caractéristique d'un joueur.", brief="Modifier un joueur")
    @commands.check(is_admin)
    async def modifier(self, ctx, nom: str, capacite: str, valeur, nombre: int=1):
        player_id = self.get_player_from_name(nom)

        if not player_id: await send_error(ctx, f"le joueur : '{nom}' n'existe pas"); return

        player = self.data_player[player_id]
        try: valeur = int(valeur)
        except: pass

        capacite = capacite.lower()
        capacities = ("courage", "force", "habileté", "rapidité", "défense", "vie", "mana", "argent")
        
        if capacite in capacities:
            player.stat[capacities.index(capacite)] += valeur
            
            if capacite != "argent":
                msg = f"__{player.name}__ {('perd', 'gagne')[valeur > 0]} {abs(valeur)} point{('', 's')[abs(valeur) > 1]} "
                if capacite == "habileté": msg += "d'Habileté"
                else: msg += f"de {capacite.capitalize()}"
            else:
                msg = f"__{player.name}__ {('perd', 'gagne')[valeur > 0]} {abs(valeur)} Drachme{('', 's')[abs(valeur) > 1]}"
            
            await ctx.send(msg)


        elif capacite == "lieu":
            player.place = valeur
            await ctx.send(f"__{player.name}__ se dirige vers {valeur}.")

        elif capacite == "objet+":
            check = player.object_add(valeur, nombre)
            nombre = ("", f" ({nombre})")[nombre > 1]
            
            if check: await ctx.send(f"__{player.name}__ récupère l'objet : '{valeur}'{nombre}.")
            else: await send_error(ctx, f"__{player.name}__ a déjà l'objet : '{valeur}'")

        elif capacite == "objet-":
            check = player.object_del(valeur, nombre)
            nombre = ("", f" ({nombre})")[nombre > 1]

            if check: await ctx.send(f"__{player.name}__ a perdu l'objet : '{valeur}'{nombre}.")
            else: await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{valeur}' ou pas en assez grande quantité")

        self.save_game()


    @commands.command(help="Supprime la totalité de la sauvegarde du jeu en cours.", brief="Supprime la sauvegarde")
    @commands.check(is_admin)
    async def formatage(self, ctx):
        global guild_id

        self.data_player.clear()
        self.data_kick.clear()
        guild_id = 0

        await ctx.send("Partie supprimée.")
        self.save_game()


    @commands.command(help="Supprime un joueur et l'empêche de créer un nouveau personnage.", brief="Kicker un joueur")
    @commands.check(is_admin)
    async def kick(self, ctx, nom: str):
        player_id = self.get_player_from_name(nom)

        if player_id:
            self.data_player.pop(player_id)
            self.data_kick.append(player_id)
            
            await ctx.send(f"__{nom}__ a été kické.\n`id : {player_id}`")
            self.save_game()

        else:
            await send_error(ctx, f"le joueur : '{nom}' n'existe pas")


    @commands.command(help="Autorise un joueur kické à revenir. L'id du joueur est à connaître.", brief="Unkick un joueur")
    @commands.check(is_admin)
    async def unkick(self, ctx, id_joueur: int):
        if id_joueur in self.data_kick:
            self.data_kick.remove(id_joueur)
            await ctx.send(f"Le joueur a été unkick.")
            self.save_game()
        else:
            await send_error(ctx, "ce joueur n'est pas kické")


    @commands.command(help="Charge la sauvegarde donnée en argument.", brief="Charger une partie")
    @commands.check(is_admin)
    async def charger(self, ctx, sauvegarde: str):
        global guild_id
        self.data_player.clear()
        self.data_kick.clear()

        data_player, data_kick, guild_id = eval(sauvegarde)
        
        for player in data_player:
            self.data_player.update({player[0]: Player(*player)})

        for i in data_kick:
            self.data_kick.append(i)

        await ctx.send("Partie chargée.")
        self.save_game()


    @commands.command(help="Renvoie le fichier de sauvegarde", brief="Obtenir la sauvegarde")
    @commands.check(is_admin)
    async def sauvegarde(self, ctx):
        self.save_game()

        with open("save.txt", "r") as file:
            await ctx.send(f"**Sauvegarde**\n```\n{file.read()}```")


    @commands.command(help="Permet d'ajouter un objet au jeu.", brief="Ajouter un objet")
    @commands.check(is_admin)
    async def ajout_objet(self, ctx, magasin: int, type_objet: int, nom: str, courage: int, force: int, habilete: int, rapidite: int, defense: int, vie: int, mana: int, argent: int, poids: int):
        check = get_official_name(nom)

        if check: await send_error(f"l'objet : '{nom}' existe déjà"); return

        table = sqlite3.connect("odyssee_shop.db")
        c = table.cursor()

        c.execute(f"""
            INSERT INTO objets VALUES ({magasin}, {type_objet}, {nom}, {courage}, {force}, {habilete}, {rapidité}, {defense}, {vie}, {mana}, {argent}, {poids})
        """)

        table.commit()
        table.close()

        await ctx.send(f"L'objet : '{nom}' a été ajouté à la base de données.")





