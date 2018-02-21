###
NB : Créer une nouvelle base de données et choisir comme Country : France

COMPTABILITE
-Installer module comptabilité et finance + account_assert

ACHATS ET STOCK :
- Changer nom société, slogan, logo
- Activer devise MGA, Mettre la devise à MGA, EUR, USD

- Mettre le dossier purchase_discount dans le répértoire addons odoo
- Installation du module purchase_heri,referentiel_heri,stock_heri,sale_heri

###Installation module comptabilité et finance et ajouter les journaux : airtel money, orange money, M Vola...###

Mettre devise dans comptabilité à MGA

Masquer les menus Demande de prix et Bon de commande (Ajout groupe Personne)

- Manage several Warehouses, each one composed by several stock locations (Invventaire/Configuration)
- Some products may be sold/purchased in different units of measure (Invventaire/Configuration)
- Les articles peuvent avoir plusieurs attributs, définissant des variantes (exemple : taille, couleur, ...)

Menu : Configuration/Technique/Précision décimale. Product Price : 2 ; Product Unit of Measure : 1  

###
Modalité de paiement :
Vendor Payment Term/Display Name
00 Day - End of Month
00 Day - Immediate Payment
07 days
07 days - 50% of advance payment
07 days - End of Month
15 Days
15 Days - 50% of advance payment
15 Days - End of Month
30 Days
30 Days - 50% of advance payment
30 Days - End of Month
45 Days
45 Days - 50% of advance payment
45 Days - End of Month
60 Days
60 Days - 33% + 33% of advance payments
60 Days - 50% of advance payment
60 Days - End of Month
###

###importer artcile###

Mettre sequence BReq pour purchase.order

###Création utilisateur, ajouter un mail dans le res partner lié
Ajouter tous les users dans Multi-devises pour voir la devise dans les BReq
Création employé, configuration de la hierachie (Employés) par rapport à l'organigramme de HERi###

Nom Menu Inventaire en Stock
Dans la traduction Description Commande fournisseur en Budget Request pour le champ traduit 'ir.model,name'
Menu variantes articles à enlever (groupe personne) 


BUDGET REQUEST STOCK : 
Adresse du vendeur: A remplir dans le res.partner (Partenaire : Heri). Dans Client/(Onglet Ventes et Achats)/ (Champ : Adresse du vendeur)

GENERAL :
Module document à installer pour les pièces jointes
###Mettre les users dans le groupe Achat HERi avec droits d'accès : bex, bex.line###

VENTES : 
###Configurer les kiosques et les clients
Mettre les personnes responsable de la ventes : dans le Ventes/Gestionnaire
Mettre les personnes responsable de la ventes dans le groupe Listes de prix de vente
Créer liste de prix de vente en Ariary et ajouter aux entrepreneurs###

Dans groupe call center ajouter res.region dans les droits d'accès.

IMMOBILISATION :
Installer le module account_asset (Lien utile : https://www.odoo.com/documentation/user/10.0/fr/accounting/others/adviser/assets.html)
