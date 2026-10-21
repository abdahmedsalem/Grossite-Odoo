# Audit de migration Food Distribution vers une architecture Odoo standard

Audit du 20 octobre 2026, Odoo 19.0-20260609. Résultats exécutables :
[results.json](results.json). Script : [audit_project.py](../../docker/audit_project.py).

## Décision technique

La réorganisation des fichiers est possible. La conversion complète vers Community,
avec les mêmes fonctions que le paquet sectoriel Enterprise, demande aussi du
développement métier. Un déplacement des fichiers et une suppression de `depends`
ne suffisent pas.

Les fonctions Community testées sont opérationnelles. Cela ne démontre pas une
équivalence du module Enterprise : celui-ci n'est installé ni dans la base actuelle,
ni dans sa copie de test. Aucune migration des modules d'origine n'a été exécutée.

## Périmètre et protection des données

- Instance utilisée : http://localhost:8073 ; base source `food_distribution`.
- Tests exécutés sur `food_distribution_audit_20261020_133630`, restaurée depuis
  un export PostgreSQL. Aucun test métier n'a écrit dans la base source.
- Filestore copié vers le nom de la base de test ; aucune tâche planifiée lancée
  pour cette base, aucun serveur HTTP supplémentaire démarré.
- Données de test créées sous savepoints, puis annulées. Contrôle final : zéro
  produit, partenaire ou journal de test restant dans la copie.
- Modules d'origine et configuration Docker conservés. Seuls les scripts,
  documents d'audit et l'exclusion Git de `backups/` sont ajoutés/modifiés.
- Les sauvegardes sont locales dans `backups/`, exclu de Git. Elles contiennent
  des données de la base et doivent rester privées.

Sauvegardes réalisées :

| Fichier | Contenu | Vérification |
| --- | --- | --- |
| `backups/food_distribution-20261020-133630.dump` | Export PostgreSQL au format custom | Restauration réussie dans la base de test |
| `backups/food_distribution-filestore-20261020-133630.tar.gz` | Pièces jointes et fichiers Odoo | Archive créée et exportée ; pas de restauration complète à blanc DB + archive |
| `backups/source-modules-20261020-133630.zip` | Les deux modules et `compose.yaml` | Archive créée ; empreintes SHA-256 des XML dans `results.json` |

Il s'agit de sauvegardes à chaud prises successivement, sans gel des écritures
utilisateur. Leur cohérence atomique base/filestore n'est donc pas garantie.
La sauvegarde définitive avant migration devra être prise pendant un arrêt contrôlé
des écritures, avec les fichiers de configuration privés conservés séparément.

## État actuel réellement observé

Les applications `sale_management`, `purchase`, `stock`, `mrp`, `account` et
`product_expiry` sont installées. `food_distribution` et `base_industry_data` sont
non installés. Les personnalisations alimentaires de ces deux paquets n'existent
donc pas encore dans la base actuelle.

Société : **StockPro Demo** ; pays : **MR** ; devise : **USD** ; plan comptable :
`generic_coa`, 51 comptes. Ces réglages sont observés, pas corrigés par cet audit.
Le choix USD/MRU et la configuration fiscale devront être validés séparément.
Les tests de facturation utilisent des comptes synthétiques annulés ensuite ;
ils ne valident pas le paramétrage fiscal réel.

Le chemin `/mnt/enterprise-addons` configuré n'existe pas dans le conteneur observé.
Odoo l'ignore et démarre ; cet avertissement ne bloque pas les applications
Community. Aucun montage n'a été changé pendant l'audit.

## Inventaire du code

| Élément | `food_distribution` | `base_industry_data` |
| --- | ---: | ---: |
| Fichiers XML du manifeste | 40 : 27 données + 13 démo | 6 : 2 données + 4 démo |
| Balises `record` | 189 | 48 |
| Modèles personnalisés | 3 | 0 |
| Champs personnalisés | 21 | 0 |
| Vues `ir.ui.view` | 7 | 0 |
| Appels XML `function` | 49 | 0 |
| Autres éléments XML | 1 template, 1 menuitem | — |
| Licence déclarée | `OEEL-1` | `OEEL-1` |

Les 46 XML ont été parsés ; les ressources des attributs `file` ont été vérifiées,
sans fichier manquant détecté. Les traductions et ressources statiques doivent
également être conservées lors de la migration. La licence déclarée ne doit pas
être changée automatiquement lors d'une réorganisation.

### Modèles et champs à porter

| Modèle | Contenu | Points à conserver |
| --- | --- | --- |
| `x_nutritional_facts` | Référentiel nutritionnel, 6 champs | Nom, archivage, séquence, parent, unité, chatter et suivi des modifications |
| `x_product_template_ingredients` | Lignes d'ingrédients, 5 champs | Produit, ingrédient, proportion, séquence, allergène lié en lecture seule |
| `x_product_template_nutritional_fact` | Valeurs nutritionnelles, 6 champs | Produit, fait nutritionnel, valeur pour 100 g, unité et séquence liées non stockées |
| `product.template` | 4 champs ajoutés | Note d'étiquette, allergène, ingrédients et valeurs nutritionnelles |
| `res.company` / `res.config.settings` | 2 champs ajoutés | Activation des étiquettes et relation au réglage de la société |

Pour la conversion Python, conserver les noms techniques, les relations, les
tables, les types, `required`, `readonly`, `store`, les champs liés, les valeurs
par défaut, les libellés, les traductions et le comportement du chatter. Ne pas
renommer `x_name`/`x_active` ou les tables dans la première étape. Le nom affiché
et le mécanisme d'archivage doivent être explicitement vérifiés en Python.

`ir_default.xml` définit l'activation par défaut du référentiel nutritionnel.
Le champ `x_unit_id` nutritionnel et `x_is_allergen` des ingrédients sont liés et
non stockés ; une conversion en champs indépendants changerait le comportement.

Six enregistrements d'accès accordent lecture/création/modification aux utilisateurs
internes et tous les droits aux administrateurs sur les trois modèles. Aucun
`ir.rule` propre à ces modèles n'a été trouvé. Il faudra tester les rôles et le
comportement multi-société, sans inventer de nouvelles restrictions pendant le portage.

## Dépendances et compatibilité Community

| Dépendance déclarée | Code local | Action pour Community |
| --- | --- | --- |
| `appointment_account_payment` | Absent | Examiner le produit de réservation référencé ; remplacer la fonction si elle est requise |
| `base_industry_data` | Présent, non installé | Porter le socle en supprimant le couplage fonctionnel à Knowledge, après remplacement du guide |
| `mrp_mps` | Absent | Développer/intégrer un équivalent du planning directeur et des prévisions |
| `product_expiry` | Présent, installé | Conserver la dépendance standard |
| `project_mrp_workorder_account` | Absent | Définir et reproduire les liaisons projet/coûts/ordres de travail nécessaires |
| `purchase_mrp` | Présent, installé | Conserver |
| `quality_mrp_workorder_worksheet` | Absent | Remplacer contrôles qualité, intégration fabrication et feuilles de travail |
| `sale_mrp` | Présent, installé | Conserver |
| `sale_planning` | Absent | Reproduire les fonctions de planification nécessaires ; elles ne sont pas couvertes par le test fabrication |
| `sale_purchase_project` | Présent, non installé | Dépendance Community disponible, à inclure/tester si conservée |
| `sale_purchase_stock` | Présent, installé | Conserver |
| `spreadsheet_sale_management` | Absent | Reproduire les tableaux et analyses requis ; une liste ou un graphique ne prouve pas l'équivalence |
| `stock_barcode` | Absent | Prévoir une interface de scan équivalente ; les champs/code-barres imprimés standards ne la remplacent pas |
| `web_studio` | Absent | Porter champs/vues/actions vers du code ; l'éditeur Studio lui-même n'est pas recréé par ce portage |
| `knowledge` via `base_industry_data` | Absent | Remplacer pages, favoris et visite guidée Knowledge |
| `base` via `base_industry_data` | Présent, installé | Conserver |

Huit dépendances directes de `food_distribution` sont absentes, plus `knowledge`
via son socle. L'absence de code empêche d'auditer l'intégralité de leur comportement.
Le manifeste suffit à identifier les besoins, pas à déduire une équivalence complète.

`base.automation` n'est pas disponible dans le registre courant, mais son module
`base_automation` est un composant Community à examiner/ajouter explicitement si
l'automatisation est conservée. Il ne faut pas le compter comme une fonction
forcément réservée à Enterprise.

### Blocages concrets constatés

- Installation d'origine refusée par Odoo : dépendance
  `appointment_account_payment` indisponible. C'est un rejet attendu et testé.
- **16 enregistrements `quality.point`** à conserver : ingrédients consommés,
  instructions, pH, température, lots et impression d'étiquettes.
- **3 enregistrements `mrp.production.schedule`** dans les démos ; 11 appels XML
  aux méthodes de prévision/réapprovisionnement indisponibles dans le registre courant.
- **12 appels `quality.check.do_pass`** indisponibles dans le scénario de démo.
- Knowledge : article, favori, lien dans un message et visite guidée JavaScript.
- 3 champs de configuration non fournis par les applications installées :
  `group_mrp_wo_tablet_timer`, `mrp_mps_show_actual_demand` et
  `mrp_mps_show_actual_replenishment`.
- 6 références externes non résolues : une référence au produit de réservation,
  trois types de contrôle `mrp_workorder`, un type `quality` et un type
  `quality_control`. La liste exacte est dans `results.json`.

Les absences des champs `x_…` et du modèle `x_nutritional_facts` dans la base
courante sont attendues : leurs déclarations sont bien présentes dans le code du
module non installé. Ce ne sont pas des preuves supplémentaires de dépendances Enterprise.
La référence partenaire `res_users_7_res_partner`, d'abord inconnue du registre,
est bien générée lors de l'import des utilisateurs : ce point a été testé.

### Logique cachée dans les données XML

`data/res_config_settings.xml` mélange paramètres, deux champs, une action serveur,
une automatisation, une vue et deux appels de méthodes. L'action active/désactive
les vues d'étiquette, le menu nutritionnel et deux contrôles qualité, et change le
format papier du rapport de lots. Elle doit être portée et testée en entier.

`data/mrp_bom_post.xml` recalcule des coûts et modifie la méthode de réservation
d'un type d'opération de fabrication. Sa recherche utilise le nom anglais
`Manufacturing` : le portage devrait choisir un identifiant technique et tester
les entrepôts et traductions, sans changer le résultat métier attendu.

Les démos confirment achats/ventes, ajustent des stocks, valident des réceptions,
livraisons, fabrications et contrôles qualité. Elles ne doivent pas être chargées
comme de simples données de configuration sur une base utilisateur. Le fichier
`demo/res_company.xml` remplace notamment le nom et l'adresse de la société.

## Tests exécutés et résultats

**11 contrôles réussis**, dont un rejet d'installation attendu. Les quantités et
états finaux sont enregistrés dans `results.json`.

| Contrôle | Résultat vérifié |
| --- | --- |
| Installation originale | Refus attendu pour dépendance absente |
| Plan de déplacement | 46 entrées de manifeste, ordre conservé, aucune collision de destination |
| Vente et livraison | Commande confirmée ; livraison terminée ; 2 unités livrées |
| Achat et réception | Achat confirmé ; réception terminée ; 3 unités reçues |
| Lot et péremption | Dates calculées ; date d'alerte antérieure à la péremption ; 4 unités liées au lot |
| Fabrication | 2 unités produites ; mouvements composants terminés |
| Facturation | Facture comptabilisée, total 24 ; écriture équilibrée, comptes synthétiques |
| Références de démo | Partenaire utilisateur généré ; catégories chargées après contacts |
| Héritage des vues | 4 architectures héritées appliquées aux parents Community sans erreur XPath |
| Parcours alimentaire lié | Achat de 5, réception du lot, livraison de 2 du même lot, facture liée à la vente, stock restant 3 |
| Utilisateur non administrateur | Menus Ventes/Achats/Inventaire/Fabrication/Facturation visibles et accès en lecture aux modèles métier |

Le contrôle XPath ne valide ni le rendu navigateur, ni tous les champs d'une vue,
ni un PDF final. Le test des droits vérifie visibilité/lecture ; il ne couvre
pas toutes les écritures ni les restrictions multi-société. Les autres tests ORM
s'exécutent avec les droits du shell, sur la copie uniquement.

Non validés à ce stade : interface de scan, fonctions qualité, MPS, feuilles de
travail, planification, tableaux de bord Enterprise, comportement de l'éditeur
Studio, paiement, réconciliation, retours, multi-entrepôt, multi-société et
impression finale des étiquettes. L'installation du module d'origine et sa
comparaison avec un futur port Community restent bloquées/non réalisées.

## Architecture et séquence recommandées

```text
addons/
  food_distribution_core/
    __init__.py
    __manifest__.py
    models/           # nutrition, ingrédients, produits, réglages
    views/            # formulaires, listes, recherches, menus
    security/         # groupes et accès équivalents
    report/           # rapports QWeb et format papier
    data/             # référentiels et paramètres
    demo/             # démonstrations facultatives
    tests/            # régressions des fonctions réellement portées
    static/
    i18n/
  food_distribution_quality/   # équivalent qualité à développer/intégrer
  food_distribution_planning/  # équivalent des fonctions de planning requises
  food_distribution_barcode/   # interface de scan si maintien requis
```

Ces noms sont une proposition pour un port Community distinct. Pour une simple
réorganisation à comportement identique du module existant, conserver les noms
techniques `food_distribution` et `base_industry_data`. Un changement de nom de
module doit être traité comme une migration des identifiants XML, pas comme un
renommage de dossier.

1. Définir une matrice d'acceptation des fonctions Enterprise attendues à partir
   des besoins et, pour une parité exacte, d'une instance de référence accessible.
2. Déplacer d'abord les fichiers homogènes vers `views/` et `security/` en gardant
   les noms de modules, identifiants XML, octets XML et ordre du manifeste.
   Le plan détaillé figure dans `relocation_plan` de `results.json` ; il s'agit
   d'un plan, pas d'une migration déjà validée par installation.
3. Porter les 3 modèles et les 21 champs en Python, avec des tests de schéma,
   lecture/écriture, valeurs liées, défauts et droits. Sur une base où ces champs
   existent déjà, traiter explicitement le passage des métadonnées `manual` vers
   des champs définis par code, sans supprimer les colonnes.
4. Scinder `res_config_settings.xml` après définition des modèles Python et
   conserver les références nécessaires aux automatisations, ou porter leur
   logique dans des méthodes testées. Ne pas exécuter deux fois la même logique.
5. Développer/intégrer les équivalents qualité, planning, scan et documentation.
   Découper les dépendances en modules fonctionnels plutôt que déclarer tout
   l'ancien manifeste compatible par suppression de lignes.
6. Tester installation neuve et mise à jour, avec et sans démo, puis les parcours
   métier, rôles, sociétés, étiquettes PDF et reprise des données. Comparer
   comptes de lignes, identifiants et relations avant/après.
7. Effectuer une répétition de restauration ; prendre une sauvegarde cohérente ;
   appliquer la migration validée à l'instance utilisateur avec contrôle final.

## Rejouer les contrôles

La copie de test est conservée pour examen. Elle n'est pas exposée par le filtre
de bases du serveur Web. Le script refuse un nom de base ne commençant pas par
`food_distribution_audit_`.

Depuis PowerShell à la racine du projet :

```powershell
$auditDb = (Get-Content docs/audit/database.txt).Trim()
Get-Content -Raw docker/audit_project.py |
    docker compose exec -T odoo /entrypoint.sh odoo shell --database=$auditDb --no-http --max-cron-threads=0 --log-level=warn
```

Les détails sont écrits dans `/tmp/food_distribution_audit_results.json` du
conteneur Odoo. Le script affiche les résultats de chaque contrôle sans mot de passe.
L'audit ne démontre pas encore l'objectif « aucune perte » : celui-ci nécessite
le portage, des tests de migration et la validation des équivalents métier.
