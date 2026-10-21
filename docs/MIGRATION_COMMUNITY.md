# Migration Odoo 19 Community

**Déployée et vérifiée le 20 octobre 2026 sur http://localhost:8073.**
Les deux conteneurs du projet sont sains. La prévisualisation temporaire est arrêtée.

Résultats : **16 tests Odoo**, **7 parcours Community**, **12 contrôles navigateur
sur la copie** et **9 contrôles navigateur en lecture seule sur l'instance active**
réussis. Les enregistrements d'origine contrôlés sur 15 tables sont préservés et
les 46 XML des paquets d'origine sont inchangés. Aucun produit ou référentiel
créé par les tests n'a été importé dans l'instance active.

La sauvegarde cohérente finale (base, filestore et configuration privée) se trouve
dans `backups/pre-community-20261020-145921/`.
Le [bilan machine](../migration/evidence/deployment.json), les
[contrôles de conservation](../migration/evidence/live-preservation.json) et les
[résultats navigateur de l'instance active](../migration/evidence/browser-live-results.json)
décrivent les vérifications effectuées. Les écarts Enterprise restent listés plus bas.

La version portée utilise l'architecture Python/XML standard. Les originaux
`food_distribution/` et `base_industry_data/` sont conservés comme références.
Le code actif préparé pour l'instance se trouve dans `addons/` ; les sources OCA
non modifiées se trouvent dans `vendor/`.

## Organisation

```text
addons/
  base_industry_data/         # socle sans dépendance Knowledge
  food_distribution/
    models/                  # 3 modèles, extensions produits et réglages
    views/                   # écrans, menus et actions
    security/                # droits des modèles personnalisés
    data/                    # unités et référentiel nutritionnel
    report/                  # étiquettes de lots et de nomenclatures
    demo/                    # exemples facultatifs
    tests/                   # régressions fonctionnelles
    static/ et i18n/         # ressources et traductions conservées
  food_distribution_quality/ # liaison entre MRP standard et qualité OCA
  food_distribution_planning/# prévisions manuelles vers des OF standards
vendor/
  quality_control_oca/       # code OCA original, version 19.0
  provenance.json           # révision exacte et empreinte de l'archive
migration/                   # copie de travail, outils et preuves de validation
backups/                     # sauvegardes privées, exclues de Git
```

Les licences d'origine `OEEL-1` sont conservées pour les deux paquets fournis.
Le module OCA et le connecteur qualité déclarent `AGPL-3` ; le module de prévisions
déclare `LGPL-3`. La compatibilité avec Community décrit ici le fonctionnement
technique ; aucune licence d'origine n'a été remplacée par une autre.

## Réutilisation du standard

| Fonction | Traitement |
| --- | --- |
| Ventes, achats, réceptions, livraisons | Modules Community et mouvements natifs, sans modification de leur code |
| Stock, composants, nomenclatures, opérations et fabrication | MRP/Stock standards ; pas de moteur de stock personnalisé |
| Lots, traçabilité et dates de péremption | `stock` et `product_expiry` standards |
| Facturation et écritures comptables | `account` standard ; devise et fiscalité existantes conservées |
| Relations achats/ventes/projets/fabrication | Dépendances Community existantes, notamment `sale_purchase_project` |
| Analyse commerciale | Listes, graphiques et tableaux croisés natifs ; exports standards |
| Qualité : tests, mesures, réponses et inspections | Réutilisation de `quality_control_oca`, sans modification du code OCA |

Le développement spécifique porte sur les ingrédients, allergènes, données
nutritionnelles, étiquettes, liaison des inspections à la fabrication et saisie
de prévisions qui créent des ordres de fabrication natifs.

## Données et identifiants

Les trois noms de modèles `x_…`, leurs tables et les 21 champs historiques sont
conservés. Les anciens identifiants XML des champs sont maintenus comme alias
des champs Python. Les droits internes restent lecture/création/modification,
sans suppression ; les administrateurs disposent des quatre droits.

Les valeurs liées non stockées conservent ce comportement. Un champ technique
supplémentaire mémorise uniquement la séquence de tri des lignes nutritionnelles,
pour conserver le tri attendu sans demander à PostgreSQL de trier un champ non stocké.

Les réglages d'étiquettes utilisent la société courante. Les vues et rapports
standards ne sont pas globalement désactivés ou réécrits par une action serveur.
L'action d'impression alimentaire est distincte et le rapport standard reste disponible.
L'impression depuis une nomenclature utilise des enregistrements virtuels ; elle
ne crée aucun lot ni stock et n'invente pas de date de péremption.

La base actuelle ne contenait pas les modules sectoriels installés. Cette migration
valide donc le port du code et l'ajout aux applications Community existantes ; elle
ne constitue pas une reprise validée d'une base Enterprise où ces modules seraient
déjà utilisés. Le hook de reprise des métadonnées manuelles doit être testé sur une
telle base avant toute utilisation dans ce contexte différent.

Les produits, fournisseurs, nomenclatures et contrôles illustratifs sont classés
dans `demo/`. Ils ne sont pas importés dans l'instance utilisateur lors de
l'installation sans démos. Les anciennes démos qui validaient automatiquement des
achats, ventes, stocks ou fabrications ne sont pas rejouées sur les données réelles.
Leurs XML restent disponibles dans les originaux et les sauvegardes.

## Qualité

Les 16 points de l'exemple original sont convertis en tests OCA et points de liaison
aux produits/opérations. Les mesures conservent les tolérances de pH et de température ;
les autres étapes utilisent des réponses explicites. Les composants et lots sont
enregistrés par les mouvements MRP natifs, puis vérifiés dans l'inspection.

Les inspections sont générées à la confirmation d'un OF, une seule fois par point.
Les inspections non réussies empêchent la fin de fabrication. Les étapes d'étiquette
activées nécessitent la génération du rapport. Le système enregistre une demande
d'impression, pas une preuve matérielle de sortie d'une imprimante.

Les opérateurs MRP reçoivent le rôle utilisateur qualité ; les responsables MRP
reçoivent le rôle responsable qualité. Les règles multi-société OCA sont conservées,
avec une règle additionnelle sur les points de liaison.

Source du composant réutilisé : [OCA/manufacture, branche 19.0](https://github.com/OCA/manufacture/tree/19.0/quality_control_oca).
Révision vendue localement : `a9f2ec8693394b01cb0d50ce27713d7926ea922a`.

## Prévisions

Le menu **Fabrication → Food Production Forecasts** permet de saisir produit,
période, quantité et nomenclature, puis de créer un OF standard confirmé. Une
deuxième demande ne crée pas de doublon ; les données de la prévision deviennent
figées une fois l'OF créé. La suite du travail se fait dans l'OF standard.

Les 8 quantités de prévision d'exemple sont reprises en démos. Ce planning manuel
ne prétend pas reproduire le moteur MPS : il n'effectue pas de calcul de demande
nette multi-période, de propagation de prévisions indirectes ni de calcul automatique
des stocks de sécurité.

Les règles de réapprovisionnement natives restent disponibles. Elles ne sont pas
activées automatiquement sur les produits de prévision : la documentation Odoo
distingue ces mécanismes et déconseille leur cumul avec MPS sur un même produit.
[Documentation MPS Odoo 19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/manufacturing/workflows/use_mps.html).

## Écarts Enterprise restant à couvrir

| Fonction Enterprise | État du port Community |
| --- | --- |
| Éditeur Studio | Champs/vues alimentaires portés en code ; éditeur graphique général non remplacé |
| Interface complète `stock_barcode` | Codes-barres produits et rapports natifs conservés ; interface mobile de scan, GS1 et mode hors ligne non portés |
| MPS complet | Prévisions manuelles et OF standards disponibles ; moteur MPS et grille interactive non équivalents |
| Planning des ressources de `sale_planning` | Fonctions projet/MRP natives disponibles ; calendrier de ressources Enterprise non reproduit |
| Worksheets et Shop Floor Enterprise | Inspections OCA et lien opérations/OF disponibles ; écrans tablette et feuilles Enterprise non reproduits à l'identique |
| Knowledge | Texte du guide conservé dans une page HTML locale ; édition collaborative, favoris et navigation Knowledge non repris |
| Tableurs commerciaux interactifs | Analyses et exports natifs disponibles ; moteur de tableur Enterprise non remplacé |
| Rendez-vous et paiement de réservation | Référence étrangère au produit de réservation exclue du port ; application de rendez-vous payants non implémentée |
| Coûts analytiques avancés d'ordres de travail | Composants Community existants réutilisés ; parité avec l'intégration Enterprise non démontrée |

La recherche sur le dépôt officiel [OCA/stock-logistics-barcode](https://github.com/OCA/stock-logistics-barcode/issues/722)
n'a pas permis de récupérer un manifeste `stock_barcodes` installé et validé pour
la branche 19.0 au moment du portage. Aucun module d'une autre version n'a été
installé à sa place.

Ces écarts sont explicites : l'objectif d'une parité intégrale Enterprise n'est
pas déclaré atteint. Ils n'enlèvent aucune fonction des applications Community
déjà présentes dans la base actuelle.

## Validation et preuves

Les détails se trouvent dans `migration/evidence/` :

- Installation sur la copie de la base actuelle, sans démos.
- Installation neuve avec démos : 16 points qualité et 8 prévisions réellement présents.
- Tests Odoo des champs liés, archivage, droits, sociétés, rapports, qualité et prévisions.
- Sept parcours de non-régression Community repris de l'audit, dont achat → lot → vente → livraison → facture.
- Comparaison des enregistrements d'origine et colonnes métier sélectionnées sur
  15 tables avec une base témoin restaurée depuis la même sauvegarde : aucun
  enregistrement contrôlé modifié ni supprimé. Ce contrôle ne couvre pas chaque
  colonne ni chaque table de toute la base.
- Conservation des lignes alimentaires personnalisées lors d'une mise à jour des modules.
- Génération HTML et PDF d'une étiquette alimentaire.
- Chrome : applications standard, qualité, prévisions, création/enregistrement
  nutritionnel et affichage des ingrédients/allergènes/valeurs nutritionnelles.

Les scénarios automatisés et les créations navigateur ont lieu dans les bases de
test. Les exemples `MIGRATION PREVIEW` et `BROWSER Nutrition` ne doivent pas être
transférés vers l'instance utilisateur.

Les sauvegardes finales avant installation sur l'instance doivent être prises
pendant l'arrêt du conteneur Odoo, pour figer les écritures et obtenir ensemble
la base PostgreSQL et le filestore correspondants. La même base et les mêmes
volumes sont conservés lors du changement des montages de code.

## Utilisation

L'instance utilisateur reste sur **http://localhost:8073**. Les identifiants
existants sont conservés dans `.env`.

- Produits : onglet **Label** pour ingrédients, allergènes, note et nutrition.
- Inventaire → Configuration : **Nutritional Facts** et guide alimentaire.
- Lots : menu d'impression **Food & Drinks Label** ; le rapport standard reste disponible.
- Nomenclatures : impression **Food Product Label**.
- Application **Quality Control** : tests, inspections et **Food Quality Points**.
- Fabrication : **Food Production Forecasts** et onglet **Food Quality** des OF.
- Paramètres → Food Distribution : activation des étiquettes pour chaque société.

La prévisualisation reste distincte sur **http://localhost:8074**. Pour la démarrer :

```powershell
docker compose -f compose.migration.yaml --env-file migration/.env up -d
```

Pour l'instance utilisateur, les commandes habituelles restent :

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail=100 odoo
```

Les originaux racine ne sont pas les dossiers montés après migration. Les modifications
futures doivent porter sur `addons/`, puis être testées avant une mise à jour Odoo.
