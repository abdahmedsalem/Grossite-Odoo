# Migration Odoo 19 Community

**DÃ©ployÃ©e et vÃ©rifiÃ©e le 20 octobre 2026 sur http://localhost:8073.**
Les deux conteneurs du projet sont sains. La prÃ©visualisation temporaire est arrÃªtÃ©e.

RÃ©sultats : **16 tests Odoo**, **7 parcours Community**, **12 contrÃ´les navigateur
sur la copie** et **9 contrÃ´les navigateur en lecture seule sur l'instance active**
rÃ©ussis. Les enregistrements d'origine contrÃ´lÃ©s sur 15 tables sont prÃ©servÃ©s et
les 46 XML des paquets d'origine sont inchangÃ©s. Aucun produit ou rÃ©fÃ©rentiel
crÃ©Ã© par les tests n'a Ã©tÃ© importÃ© dans l'instance active.

La sauvegarde cohÃ©rente finale (base, filestore et configuration privÃ©e) se trouve
dans `backups/pre-community-20261020-145921/`.
Le [bilan machine](evidence/deployment.json), les
[contrÃ´les de conservation](evidence/live-preservation.json) et les
[rÃ©sultats navigateur de l'instance active](evidence/browser-live-results.json)
dÃ©crivent les vÃ©rifications effectuÃ©es. Les Ã©carts Enterprise restent listÃ©s plus bas.

La version portÃ©e utilise l'architecture Python/XML standard. Les originaux
`food_distribution/` et `base_industry_data/` sont conservÃ©s comme rÃ©fÃ©rences.
Le code actif prÃ©parÃ© pour l'instance se trouve dans `addons/` ; les sources OCA
non modifiÃ©es se trouvent dans `vendor/`.

## Organisation

```text
addons/
  base_industry_data/         # socle sans dÃ©pendance Knowledge
  food_distribution/
    models/                  # 3 modÃ¨les, extensions produits et rÃ©glages
    views/                   # Ã©crans, menus et actions
    security/                # droits des modÃ¨les personnalisÃ©s
    data/                    # unitÃ©s et rÃ©fÃ©rentiel nutritionnel
    report/                  # Ã©tiquettes de lots et de nomenclatures
    demo/                    # exemples facultatifs
    tests/                   # rÃ©gressions fonctionnelles
    static/ et i18n/         # ressources et traductions conservÃ©es
  food_distribution_quality/ # liaison entre MRP standard et qualitÃ© OCA
  food_distribution_planning/# prÃ©visions manuelles vers des OF standards
vendor/
  quality_control_oca/       # code OCA original, version 19.0
  provenance.json           # rÃ©vision exacte et empreinte de l'archive
migration/                   # copie de travail, outils et preuves de validation
backups/                     # sauvegardes privÃ©es, exclues de Git
```

Les licences d'origine `OEEL-1` sont conservÃ©es pour les deux paquets fournis.
Le module OCA et le connecteur qualitÃ© dÃ©clarent `AGPL-3` ; le module de prÃ©visions
dÃ©clare `LGPL-3`. La compatibilitÃ© avec Community dÃ©crit ici le fonctionnement
technique ; aucune licence d'origine n'a Ã©tÃ© remplacÃ©e par une autre.

## RÃ©utilisation du standard

| Fonction | Traitement |
| --- | --- |
| Ventes, achats, rÃ©ceptions, livraisons | Modules Community et mouvements natifs, sans modification de leur code |
| Stock, composants, nomenclatures, opÃ©rations et fabrication | MRP/Stock standards ; pas de moteur de stock personnalisÃ© |
| Lots, traÃ§abilitÃ© et dates de pÃ©remption | `stock` et `product_expiry` standards |
| Facturation et Ã©critures comptables | `account` standard ; devise et fiscalitÃ© existantes conservÃ©es |
| Relations achats/ventes/projets/fabrication | DÃ©pendances Community existantes, notamment `sale_purchase_project` |
| Analyse commerciale | Listes, graphiques et tableaux croisÃ©s natifs ; exports standards |
| QualitÃ© : tests, mesures, rÃ©ponses et inspections | RÃ©utilisation de `quality_control_oca`, sans modification du code OCA |

Le dÃ©veloppement spÃ©cifique porte sur les ingrÃ©dients, allergÃ¨nes, donnÃ©es
nutritionnelles, Ã©tiquettes, liaison des inspections Ã  la fabrication et saisie
de prÃ©visions qui crÃ©ent des ordres de fabrication natifs.

## DonnÃ©es et identifiants

Les trois noms de modÃ¨les `x_â€¦`, leurs tables et les 21 champs historiques sont
conservÃ©s. Les anciens identifiants XML des champs sont maintenus comme alias
des champs Python. Les droits internes restent lecture/crÃ©ation/modification,
sans suppression ; les administrateurs disposent des quatre droits.

Les valeurs liÃ©es non stockÃ©es conservent ce comportement. Un champ technique
supplÃ©mentaire mÃ©morise uniquement la sÃ©quence de tri des lignes nutritionnelles,
pour conserver le tri attendu sans demander Ã  PostgreSQL de trier un champ non stockÃ©.

Les rÃ©glages d'Ã©tiquettes utilisent la sociÃ©tÃ© courante. Les vues et rapports
standards ne sont pas globalement dÃ©sactivÃ©s ou rÃ©Ã©crits par une action serveur.
L'action d'impression alimentaire est distincte et le rapport standard reste disponible.
L'impression depuis une nomenclature utilise des enregistrements virtuels ; elle
ne crÃ©e aucun lot ni stock et n'invente pas de date de pÃ©remption.

La base actuelle ne contenait pas les modules sectoriels installÃ©s. Cette migration
valide donc le port du code et l'ajout aux applications Community existantes ; elle
ne constitue pas une reprise validÃ©e d'une base Enterprise oÃ¹ ces modules seraient
dÃ©jÃ  utilisÃ©s. Le hook de reprise des mÃ©tadonnÃ©es manuelles doit Ãªtre testÃ© sur une
telle base avant toute utilisation dans ce contexte diffÃ©rent.

Les produits, fournisseurs, nomenclatures et contrÃ´les illustratifs sont classÃ©s
dans `demo/`. Ils ne sont pas importÃ©s dans l'instance utilisateur lors de
l'installation sans dÃ©mos. Les anciennes dÃ©mos qui validaient automatiquement des
achats, ventes, stocks ou fabrications ne sont pas rejouÃ©es sur les donnÃ©es rÃ©elles.
Leurs XML restent disponibles dans les originaux et les sauvegardes.

## QualitÃ©

Les 16 points de l'exemple original sont convertis en tests OCA et points de liaison
aux produits/opÃ©rations. Les mesures conservent les tolÃ©rances de pH et de tempÃ©rature ;
les autres Ã©tapes utilisent des rÃ©ponses explicites. Les composants et lots sont
enregistrÃ©s par les mouvements MRP natifs, puis vÃ©rifiÃ©s dans l'inspection.

Les inspections sont gÃ©nÃ©rÃ©es Ã  la confirmation d'un OF, une seule fois par point.
Les inspections non rÃ©ussies empÃªchent la fin de fabrication. Les Ã©tapes d'Ã©tiquette
activÃ©es nÃ©cessitent la gÃ©nÃ©ration du rapport. Le systÃ¨me enregistre une demande
d'impression, pas une preuve matÃ©rielle de sortie d'une imprimante.

Les opÃ©rateurs MRP reÃ§oivent le rÃ´le utilisateur qualitÃ© ; les responsables MRP
reÃ§oivent le rÃ´le responsable qualitÃ©. Les rÃ¨gles multi-sociÃ©tÃ© OCA sont conservÃ©es,
avec une rÃ¨gle additionnelle sur les points de liaison.

Source du composant rÃ©utilisÃ© : [OCA/manufacture, branche 19.0](https://github.com/OCA/manufacture/tree/19.0/quality_control_oca).
RÃ©vision vendue localement : `a9f2ec8693394b01cb0d50ce27713d7926ea922a`.

## PrÃ©visions

Le menu **Fabrication â†’ Food Production Forecasts** permet de saisir produit,
pÃ©riode, quantitÃ© et nomenclature, puis de crÃ©er un OF standard confirmÃ©. Une
deuxiÃ¨me demande ne crÃ©e pas de doublon ; les donnÃ©es de la prÃ©vision deviennent
figÃ©es une fois l'OF crÃ©Ã©. La suite du travail se fait dans l'OF standard.

Les 8 quantitÃ©s de prÃ©vision d'exemple sont reprises en dÃ©mos. Ce planning manuel
ne prÃ©tend pas reproduire le moteur MPS : il n'effectue pas de calcul de demande
nette multi-pÃ©riode, de propagation de prÃ©visions indirectes ni de calcul automatique
des stocks de sÃ©curitÃ©.

Les rÃ¨gles de rÃ©approvisionnement natives restent disponibles. Elles ne sont pas
activÃ©es automatiquement sur les produits de prÃ©vision : la documentation Odoo
distingue ces mÃ©canismes et dÃ©conseille leur cumul avec MPS sur un mÃªme produit.
[Documentation MPS Odoo 19](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/manufacturing/workflows/use_mps.html).

## Ã‰carts Enterprise restant Ã  couvrir

| Fonction Enterprise | Ã‰tat du port Community |
| --- | --- |
| Ã‰diteur Studio | Champs/vues alimentaires portÃ©s en code ; Ã©diteur graphique gÃ©nÃ©ral non remplacÃ© |
| Interface complÃ¨te `stock_barcode` | Codes-barres produits et rapports natifs conservÃ©s ; interface mobile de scan, GS1 et mode hors ligne non portÃ©s |
| MPS complet | PrÃ©visions manuelles et OF standards disponibles ; moteur MPS et grille interactive non Ã©quivalents |
| Planning des ressources de `sale_planning` | Fonctions projet/MRP natives disponibles ; calendrier de ressources Enterprise non reproduit |
| Worksheets et Shop Floor Enterprise | Inspections OCA et lien opÃ©rations/OF disponibles ; Ã©crans tablette et feuilles Enterprise non reproduits Ã  l'identique |
| Knowledge | Texte du guide conservÃ© dans une page HTML locale ; Ã©dition collaborative, favoris et navigation Knowledge non repris |
| Tableurs commerciaux interactifs | Analyses et exports natifs disponibles ; moteur de tableur Enterprise non remplacÃ© |
| Rendez-vous et paiement de rÃ©servation | RÃ©fÃ©rence Ã©trangÃ¨re au produit de rÃ©servation exclue du port ; application de rendez-vous payants non implÃ©mentÃ©e |
| CoÃ»ts analytiques avancÃ©s d'ordres de travail | Composants Community existants rÃ©utilisÃ©s ; paritÃ© avec l'intÃ©gration Enterprise non dÃ©montrÃ©e |

La recherche sur le dÃ©pÃ´t officiel [OCA/stock-logistics-barcode](https://github.com/OCA/stock-logistics-barcode/issues/722)
n'a pas permis de rÃ©cupÃ©rer un manifeste `stock_barcodes` installÃ© et validÃ© pour
la branche 19.0 au moment du portage. Aucun module d'une autre version n'a Ã©tÃ©
installÃ© Ã  sa place.

Ces Ã©carts sont explicites : l'objectif d'une paritÃ© intÃ©grale Enterprise n'est
pas dÃ©clarÃ© atteint. Ils n'enlÃ¨vent aucune fonction des applications Community
dÃ©jÃ  prÃ©sentes dans la base actuelle.

## Validation et preuves

Les dÃ©tails se trouvent dans `docs/evidence/` :

- Installation sur la copie de la base actuelle, sans dÃ©mos.
- Installation neuve avec dÃ©mos : 16 points qualitÃ© et 8 prÃ©visions rÃ©ellement prÃ©sents.
- Tests Odoo des champs liÃ©s, archivage, droits, sociÃ©tÃ©s, rapports, qualitÃ© et prÃ©visions.
- Sept parcours de non-rÃ©gression Community repris de l'audit, dont achat â†’ lot â†’ vente â†’ livraison â†’ facture.
- Comparaison des enregistrements d'origine et colonnes mÃ©tier sÃ©lectionnÃ©es sur
  15 tables avec une base tÃ©moin restaurÃ©e depuis la mÃªme sauvegarde : aucun
  enregistrement contrÃ´lÃ© modifiÃ© ni supprimÃ©. Ce contrÃ´le ne couvre pas chaque
  colonne ni chaque table de toute la base.
- Conservation des lignes alimentaires personnalisÃ©es lors d'une mise Ã  jour des modules.
- GÃ©nÃ©ration HTML et PDF d'une Ã©tiquette alimentaire.
- Chrome : applications standard, qualitÃ©, prÃ©visions, crÃ©ation/enregistrement
  nutritionnel et affichage des ingrÃ©dients/allergÃ¨nes/valeurs nutritionnelles.

Les scÃ©narios automatisÃ©s et les crÃ©ations navigateur ont lieu dans les bases de
test. Les exemples `MIGRATION PREVIEW` et `BROWSER Nutrition` ne doivent pas Ãªtre
transfÃ©rÃ©s vers l'instance utilisateur.

Les sauvegardes finales avant installation sur l'instance doivent Ãªtre prises
pendant l'arrÃªt du conteneur Odoo, pour figer les Ã©critures et obtenir ensemble
la base PostgreSQL et le filestore correspondants. La mÃªme base et les mÃªmes
volumes sont conservÃ©s lors du changement des montages de code.

## Utilisation

L'instance utilisateur reste sur **http://localhost:8073**. Les identifiants
existants sont conservÃ©s dans `.env`.

- Produits : onglet **Label** pour ingrÃ©dients, allergÃ¨nes, note et nutrition.
- Inventaire â†’ Configuration : **Nutritional Facts** et guide alimentaire.
- Lots : menu d'impression **Food & Drinks Label** ; le rapport standard reste disponible.
- Nomenclatures : impression **Food Product Label**.
- Application **Quality Control** : tests, inspections et **Food Quality Points**.
- Fabrication : **Food Production Forecasts** et onglet **Food Quality** des OF.
- ParamÃ¨tres â†’ Food Distribution : activation des Ã©tiquettes pour chaque sociÃ©tÃ©.

La prÃ©visualisation reste distincte sur **http://localhost:8074**. Pour la dÃ©marrer :

```powershell
docker compose -f compose.migration.yaml --env-file migration/.env up -d
```

Pour l'instance utilisateur, les commandes habituelles restent :

```powershell
docker compose up -d
docker compose ps
docker compose logs --tail=100 odoo
```

Les originaux racine ne sont pas les dossiers montÃ©s aprÃ¨s migration. Les modifications
futures doivent porter sur `addons/`, puis Ãªtre testÃ©es avant une mise Ã  jour Odoo.


