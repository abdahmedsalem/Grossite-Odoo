# 2. Comprendre Odoo pour ce projet

[Retour au guide principal](../README.md)

## Les mots essentiels

| Terme | Explication pour StockPro |
| --- | --- |
| Société | L’entreprise gérée : StockPro Demo |
| Contact | Une personne ou une entreprise, par exemple un fournisseur ou une boutique |
| Produit | Un article acheté ou vendu, par exemple du riz |
| Entrepôt | Le dépôt qui contient les marchandises |
| Réception | L’entrée physique des marchandises achetées |
| Livraison | La sortie physique des marchandises vendues |
| Facture | Le document qui établit le montant à payer |
| Paiement | Le règlement enregistré et rapproché avec la facture |
| Application / module | Une fonctionnalité installable d’Odoo ; une application peut installer plusieurs dépendances |
| Addons | Dossiers de modules supplémentaires ; les paquets sectoriels fournis ne sont pas installés |
| Community | Édition libre utilisée ici |
| Enterprise | Édition avec des modules supplémentaires soumis à une licence distincte |

## Exemple de circuit à tester

1. **Contacts** : créer un fournisseur et une boutique fictifs.
2. **Produits** : créer un article, son prix d’achat, son prix de vente et son unité.
3. **Achats** : commander au fournisseur.
4. **Inventaire** : réceptionner la marchandise et vérifier le stock.
5. **Ventes** : saisir la commande de la boutique.
6. **Inventaire** : valider sa livraison et vérifier la sortie de stock.
7. **Facturation** : établir la facture et enregistrer un paiement partiel.
8. Vérifier le reste dû et les quantités finales.

Ce circuit décrit le travail à réaliser ; il ne constitue pas un test déjà réussi dans cette base.

## Configurer avant de développer

Les modules standards sont fournis dans l’image Docker `odoo:19.0`. Ils ne sont pas copiés dans ce projet. Il n’est pas nécessaire de créer un module personnalisé tant qu’une configuration native suffit.

Les dossiers `food_distribution/` et `base_industry_data/` contiennent des paquets sectoriels Enterprise non installés. Ils ne correspondent pas aux applications Community déjà installées dans la base.

Un dossier Odoo `static/` peut contenir des images, du JavaScript ou des ressources utilisées par un module. Il ne faut pas effacer automatiquement ce dossier dans un module utilisé. Ici, ces ressources appartiennent aux deux paquets Enterprise non utilisés. Leur suppression doit tenir compte des manifestes et des références XML.

## Prochaines étapes du MVP

- Corriger et vérifier la devise MRU ; vérifier la configuration de facturation avant toute facture de test.
- Créer riz, sucre, huile, lait et boissons, avec les conditionnements appropriés.
- Créer trois fournisseurs et cinq boutiques fictifs.
- Exécuter le circuit et noter quantités, montants, paiement et reste dû.
- Vérifier dans l’édition installée les rapports disponibles, y compris les marges avant de promettre leur disponibilité.
