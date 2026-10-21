{
    'name': 'Food Distribution Quality', 'version': '19.0.1.0.0',
    'license': 'AGPL-3', 'author': 'Community migration', 'category': 'Manufacturing/Quality',
    'depends': ['food_distribution', 'quality_control_oca'],
    'data': ['security/security.xml', 'security/ir.model.access.csv', 'views/quality_views.xml'],
    'demo': ['demo/food_quality_points.xml'],
    'installable': True,
}
