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
        global data_admin
        self.data_player, self.data_kick, self.guild_id = savefile
        self.PREFIX = config["PREFIX"]
        data_admin = config["ADMIN"]


    def save_game(self):
        for player_id in self.data_player:
            player = self.data_player[player_id]
            player.max_weight = 5 * (player.stat[1] + 1)
        export_save(self.data_player, self.data_kick, self.guild_id)


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
            embed = discord.Embed(title="Rubrique des commandes administrateur", description=f"Entrez : `{self.PREFIX}aide_admin <commande>` pour plus d'informations.", color=8421504)
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
            
            stat = stat_gen([1 for _ in range(5)], randint(1, level + 2), True)

            self.data_player.update({new_player_id : Player(new_player_id, nom, espece, '', stat)})
            await ctx.send(f"{nom}, un(e) {espece}, est apparu(e).")

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


    @commands.command(help="Permet de mofifier chaque caractéristique d'un joueur.\n\n__Caractétistiques connues :__ les capacités et statistiques, l'inventaire, le lieu, les états.", brief="Modifier un joueur")
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
            check = player.object_add(valeur, nombre)
            nombre = ("", f" ({nombre})")[nombre > 1]
            
            if check: await ctx.send(f"__{player.name}__ récupère l'objet : '{valeur}'{nombre}.")
            else: await send_error(ctx, f"__{player.name}__ a déjà l'objet : '{valeur}'")

        elif capacite == "objet-":
            check = player.object_del(valeur, nombre)
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
            check = player.power_sub(nom.lower())
            nom = nom.capitalize()

            if check == 0:
                await send_error(ctx, f"le pouvoir '{nom} n'existe pas")
            elif check == 1:
                await send_error(ctx, f"__{player.name}__ n'a pas le pouvoir : '{nom}'")
            else:
                await ctx.send(f"__{player.name}__ oublie le pouvoir : '{nom}'.")

        elif capacite == "état":
            state = get_state_by_name(valeur)
            if state + 1:
                player.state = state
                await ctx.send(f"__{player.name}__ devient {valeur}.")
            else:
                await send_error(ctx, f"{valeur} n'est pas un état connu")

        elif capacite == "compétence+":
            check = player.have_abilities(valeur)
            if player.add_abilities(valeur, check) == 1:
                await ctx.send(f"__{player.name}__ gagne la compétence : '{valeur}'.")
            else:
                await ctx.send(f"__{player.name}__ gagne un point sur la compétence : '{valeur}'.")

        elif capacite == "compétence-":
            check = player.have_abilities(valeur)
            if check == -1:
                await send_error(ctx, f"__{player.name}__ ne possède pas la compétence : '{valeur}'")
            else:
                if player.sub_abilities(valeur, check) == 1:
                    await ctx.send(f"__{player.name}__ a perdu la compétence : '{valeur}'.")
                else:
                    await ctx.send(f"__{player.name}__ a perdu un point sur la compétence : '{valeur}'.")

        
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
                await ctx.send(f"L'objet '{objet}' de __{player.name}__ {('perd', 'gagne')[valeur > 0]} {valeur} point{('', 's')[valeur > 1]} en {capacite.capitalize()}.")
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


    @commands.command(help="Charge la sauvegarde donnée en argument. La sauvegarde doit être en fichier joint", brief="Charger une partie")
    @commands.check(is_admin)
    async def charger(self, ctx):
        global guild_id
        self.data_player.clear()
        self.data_kick.clear()

        data_player, data_kick, guild_id = eval(await ctx.message.attachments[0].read())
        
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
            await ctx.send(f"**Sauvegarde**", file=discord.File("save.txt"))


    @commands.command(help="Permet d'ajouter un objet au jeu. 'magagin' et 'type_objet' sont les id et non les noms.\n\n__Magasins :__\n" + "\n".join([f"{index} - {value[0]}" for index, value in enumerate(get_shop_name())]) + "\n\n__Types :__\n" + "\n".join([f"{index} - {value}" for index, value in get_all_types()]), brief="Ajouter un objet")
    @commands.check(is_admin)
    async def ajout_objet(self, ctx, magasin: int, type_objet: int, nom: str, courage: int, force: int, habilete: int, rapidite: int, intelligence: int, defense: int, vie: int, mana: int, argent: int, poids: int):
        check = get_official_name(nom)
        if check: await send_error(f"l'objet : '{nom}' existe déjà"); return

        table = sqlite3.connect("BDD/odyssee_shop.db")
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
                        fighters[defender].state = get_state_by_name("blessé")
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

        pnj.stat_sub(pnj_weapon.stat)
        target.stat_sub(target_weapon.stat)

        self.save_game()


    @commands.command(help="Fait passer la nuit pour tous les PnJ", brief="Fait dormir les PnJ")
    @commands.check(is_admin)
    async def nuit(self, ctx):
        pnj_names = []
        for pnj_id in self.data_player:
            if pnj_id > 0: continue
            pnj = self.get_player_from_id(pnj_id)
            pnj_names.append(pnj.name)

            lvl = pnj.get_level()
            max_mana = lvl * 5
            
            # Régénération de la vie
            if pnj.stat[6] < 100 + (lvl - 1) * 50:
                pnj.stat[6] += 5 * lvl

            # régénération de la mana
            if pnj.state != 3 and pnj.stat[7] < 5 + (lvl - 1):
                pnj.stat[7] += 1 + (lvl // 2)

            # Empoisonné
            if pnj.state == 1:
                pnj.stat[6] -= random(0, 5 * lvl)

            # Inconscient
            if pnj.state == 2:
                pnj.state = 0
            
            # Blessé
            if pnj.state == 3 and pnj.stat[6] >= 100:
                pnj.state = 0
            
            # Endormi
            if pnj.state == 4:
                pnj.state = 0
            
        if len(pnj_names) == 1:
            await ctx.send(f"__{pnj_names[0]}__ a dormi.")
        elif len(pnj_names) > 1:
            await ctx.send(f"__{', '.join(pnj_names)}__ ont dormi.")
        
        self.save_game()


    @commands.command(help="Permet de faire en sorte qu'un PnJ utilise un de ses pouvoirs", brief="Utiliser un pouvoir d'un PnJ")
    @commands.check(is_admin)
    async def pnj_pouvoir(self, ctx, joueur: str, nom: str, adversaire: str=None):
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

        self.save_game()
