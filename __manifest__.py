{
    'name': 'Order Invoice',
    'author': 'CygnusOne',
    'License': 'LGPL-3',
    'version': '18.0.1.0',
    'depends': [
        'sale',
        'account',
        'web',
    ],
    'data': [
        'security/security.xml',
        'views/custom_report_invoice.xml',
        'views/sale_order_views.xml',
        'views/menu.xml'
    ],
    'installable': True,
}
