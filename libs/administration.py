import discord
from discord.ext import commands
import json

from libs.lib_odyssee import *

guild_id, data_admin = None, {}


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


async def is_admin(ctx):
    if str(ctx.guild.id) in data_admin and ctx.author.id in data_admin[str(ctx.guild.id)]:
        return True
    else:
        await send_error(ctx, "commande non-autorisée")
        return False


class AdminCommands(commands.Cog):
    def __init__(self, config, savefile):
        global data_admin
        self.data_player, self.data_kick, self.guild_id = savefile
        self.PREFIX = config["PREFIX"]
        data_admin = config["ADMIN"]


    def save_game(self):
        export_save(self.data_player, self.data_kick, self.guild_id)


    def get_player_from_id(self, player_id):
        if player_id in self.data_player:
            return self.data_player[player_id]
        else:
            return None


    def get_player_from_name(self, player_name):
        player_name = player_name.lower()
        for player_id in self.data_player:
            if self.data_player[player_id].name.lower() == player_name:
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

            await ctx.send(embed=embed)
        
        else:
            fields = []
            for cmnd in self.get_commands():
                fields.append((cmnd.brief, get_syntax(cmnd)))
            
            for embed in make_embed(fields, f"Rubrique des commandes administrateur", f"Entrez : `{self.PREFIX}aide_admin <commande>` pour plus d'informations."):
                await ctx.send(embed=embed)


    @commands.command(name="joueur+", help="Permet d'ajouter un personnage non jouable au jeu en cours. Préciser l'espèce du joueur et son nom.", brief="Ajouter un PnJ")
    @commands.check(is_admin)
    async def joueur_plus(self, ctx, nom: str, espece: str, niveau: int=0):
        if self.get_player_from_name(nom):
            await send_error(ctx, f"le joueur : '{nom}' existe déjà")
        else:
            if niveau <= 0: niveau = randint(1, get_avg_level(self.data_player) + 2)
            new_player_id = min(self.data_player.keys()) - 1
            if new_player_id > 0: new_player_id = -1
            
            stat = stat_gen([1 for _ in range(5)], niveau, True)

            self.data_player.update({new_player_id : Player(new_player_id, nom, espece, '', stat)})
            await ctx.send(f"{nom}, un(e) {espece} de niveau {niveau}, est apparu(e).")

            self.save_game()


    @commands.command(name="joueur-", help="Permet de supprimer un joueur sans le kicker.", brief="Supprimer un joueur")
    @commands.check(is_admin)
    async def joueur_moins(self, ctx, nom: str):
        player_id = self.get_player_from_name(nom)

        if player_id:
            self.data_player.pop(player_id)
            await ctx.send(f"Le joueur : __{nom}__ a été supprimé.")

            self.save_game()
        else:
            await send_error(ctx, f"le joueur : '{nom}' n'existe pas")


    @commands.command(help="Permet de mofifier chaque caractéristique d'un joueur.\n\n__Caractétistiques connues :__ les capacités et statistiques, l'inventaire, le lieu, les états, les pouvoirs et les compétences.", brief="Modifier un joueur")
    @commands.check(is_admin)
    async def modifier(self, ctx, nom: str, capacite: str, valeur, nombre: int=1):
        player_id = self.get_player_from_name(nom)
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
                else: msg += f"de {capacite.capitalize()}"
            else:
                msg = f"__{player.name}__ {('perd', 'gagne')[valeur > 0]} {abs(valeur)} Drachme{('', 's')[abs(valeur) > 1]}"
            
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
            if state + 1:
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

        
        self.save_game()

    @commands.command(help="Permet de modifier les statistiques d'un objet possédé par un joueur.", brief="Permet de modifier les caractéristique d'une arme")
    @commands.check(is_admin)
    async def modifier_objet(self, ctx, nom: str, objet:str, capacite: str, valeur: int):
        player_id = self.get_player_from_name(nom)
        if not player_id: await send_error(ctx, f"le joueur : '{nom}' n'existe pas"); return

        player = self.data_player[player_id]
        index, obj = player.have(objet)
        
        if index == -1:
            await send_error(ctx, f"__{player.name}__ ne possède pas l'objet : '{objet}'")
        else:
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
                    await ctx.send(f"Le type de l'objet '{objet}' de __{player.name}__ est devenu : '{new_type}'")
                else:
                    await send_error(ctx, f"{valeur} n'est pas l'indice d'un type connu")

            else:
                await send_error(ctx, f"'{capacite}' n'est pas une capacité connue")

        self.save_game()


    @commands.command(help="Supprime la totalité de la sauvegarde du jeu en cours.", brief="Supprime la sauvegarde")
    @commands.check(is_admin)
    async def formatage(self, ctx):
        self.data_player.clear()
        self.data_kick.clear()
        self.guild_id = 0

        await ctx.send("Partie supprimée.")
        self.save_game()


    @commands.command(help="Supprime un joueur et l'empêche de créer un nouveau personnage.", brief="Kick un joueur")
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


    @commands.command(help="Charge la sauvegarde donnée en argument. La sauvegarde doit être en fichier joint", brief="Charger une partie")
    @commands.check(is_admin)
    async def charger(self, ctx):
        global guild_id
        self.data_player.clear()
        self.data_kick.clear()

        data = json.loads(await ctx.message.attachments[0].read())
        data_player, data_kick, guild_id = data["players"], data["kicks"], data["guild_id"]
        
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

        with open("save.json", "r") as file:
            await ctx.send(f"**Sauvegarde**", file=discord.File("save.json"))


    @commands.command(help="Permet d'ajouter un objet au jeu. 'magagin' et 'type_objet' sont les id et non les noms.\n\n__Magasins :__\n" + "\n".join([f"{index} - {value[0]}" for index, value in enumerate(get_shop_name())]) + "\n\n__Types :__\n" + "\n".join([f"{index} - {value}" for index, value in get_all_types()]), brief="Ajouter un objet")
    @commands.check(is_admin)
    async def ajout_objet(self, ctx, magasin: int, type_objet: int, nom: str, courage: int, force: int, habilete: int, rapidite: int, intelligence: int, defense: int, vie: int, mana: int, argent: int, poids: int):
        check = get_official_name(nom)
        if check: await send_error(f"l'objet : '{nom}' existe déjà"); return

        table = sqlite3.connect("BDD/odyssee_objects.db")
        c = table.cursor()

        c.execute(f"INSERT INTO objets VALUES ({magasin}, {type_objet}, '{nom}', {courage}, {force}, {habilete}, {rapidite}, {intelligence}, {defense}, {vie}, {mana}, {argent}, {poids})")

        table.commit()
        table.close()

        await ctx.send(f"L'objet : '{nom}' a été ajouté à la base de données.")


    @commands.command(help="Un joueur se fait attaquer par un PnJ", brief="Attaquer un joueur")
    @commands.check(is_admin)
    async def pnj_combat(self, ctx, joueur: str, adversaire: str, arme: str=None):
        pnj = self.get_player_from_name(joueur)
        if not pnj: await send_error(ctx, f"{joueur} n'existe pas") ; return
        pnj = self.data_player[pnj]
        if pnj.id > 0 or pnj.state in (2, 4): await send_error(ctx, f"__{pnj.name}__ n'est pas un PnJ ou n'est pas en état de se battre") ; return

        target = self.get_player_from_name(adversaire)
        if not target: await send_error(ctx, f"{adversaire} n'est pas un joueur enregistré") ; return
        target = self.data_player[target]

        # Arme du joueur
        if arme:
            pnj_weapon, check = weapon_check(pnj, target, arme)
            if check == 1: await send_error(ctx, f"__{pnj.name}__ ne possède pas l'objet : '{arme}'"); return
            elif check == 2: await send_error(ctx, f"__{pnj.name}__ et __{target.name}__ ne sont pas au même endroit"); return
            elif check == 3: await send_error(ctx, f"__{pnj.name} n'a pas de projectile pour tirer"); return

        else:
            if target.place != pnj.place:
                await send_error(ctx, f"__{pnj.name}__ et __{target.name}__ ne sont pas au même endroit")
                return
        
        if not pnj_weapon: pnj_weapon = Object("ses mains", "ses mains", [int(i == 8) for i in range(9)], -1, -1)

        # Arme de l'adversaire
        target_can_fight, target_weapon = weapon_select(target)
        if target_weapon.object_type != 4 and target.place != pnj.place: target_can_fight = False


        pnj.stat_add(pnj_weapon.stat)
        target.stat_add(target_weapon.stat)

        message = ""

        fighters, target_index = phase_1(pnj, target)

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
                else: message += f" avec {pnj_weapon.name}"

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
                            check = fighters[attacker].object_add(*fighters[attacker].have(obj.name), obj.quantity, obj.name)
                            if check: loot += f" ❖ {obj.name}{('', f' ({obj.quantity})')[obj.quantity > 1]}\n"

                        self.data_player.pop(fighters[defender].id)

                        message += loot
                        end = True
                else:
                    message += f" et manque sa cible.\n"

            if end: break

        await ctx.send(message)

        pnj.stat_sub(pnj_weapon.stat)
        target.stat_sub(target_weapon.stat)

        self.save_game()


    @commands.command(help="Fait dormir les PnJ", brief="Fait dormir les PnJ")
    @commands.check(is_admin)
    async def pnj_dormir(self, ctx):
        npc_names = []
        for npc_id in self.data_player:
            if npc_id > 0: continue
            npc = self.get_player_from_id(npc_id)
            npc_names.append(npc.name)

            lvl = npc.get_level()
            max_mana = lvl * 5
            
            # Régénération de la vie
            if npc.stat[6] < 100 + (lvl - 1) * 25:
                if npc.state == 0: npc.state = 3
                npc.stat[6] += 5 * lvl

            # régénération de la mana
            if npc.state != 3 and npc.stat[7] < 5 + (lvl - 1):
                npc.stat[7] += 1 + (lvl // 2)

            # Empoisonné
            if npc.state == 1:
                npc.stat[6] -= random(1, 12) * lvl

            # Inconscient, endormi
            if npc.state in (2, 4):
                npc.state = 0
            
            # Blessé
            if npc.state == 3 and npc.stat[6] >= 100 + (lvl - 1) * 25:
                npc.state = 0
            
        if len(npc_names) == 1:
            await ctx.send(f"__{npc_names[0]}__ a dormi.")
        elif len(npc_names) > 1:
            await ctx.send(f"__{', '.join(npc_names)}__ ont dormi.")
        
        self.save_game()


    @commands.command(help="Permet de faire en sorte qu'un PnJ utilise un de ses pouvoirs", brief="Utiliser un pouvoir d'un PnJ")
    @commands.check(is_admin)
    async def pnj_pouvoir(self, ctx, joueur: str, nom: str=None, adversaire: str=None):
        pnj = self.get_player_from_name(joueur)
        if not pnj: await send_error(ctx, f"{joueur} n'est pas un joueur enregistré"); return
        pnj = self.data_player[pnj]
        if pnj.id > 0 or pnj.state in (2, 4): await send_error(ctx, f"__{pnj.name}__ n'est pas un PnJ ou n'est pas en état de se battre") ; return


        if adversaire:
            name = adversaire
            adversaire = self.get_player_from_name(adversaire)
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

        self.save_game()
