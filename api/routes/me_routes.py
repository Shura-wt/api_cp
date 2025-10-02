from flask import Blueprint, jsonify
from flasgger import swag_from
from .auth import _get_current_user

me_bp = Blueprint('me_bp', __name__)

@me_bp.route('/me', methods=['GET'])
@swag_from({
    'tags': ['Authentication'],
    'description': 'Obtenir l\'utilisateur courant et la liste des sites accessibles. Nécessite un header Authorization: Bearer <token>.',
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Bearer <token>'
        }
    ],
    'responses': {
        '200': {
            'description': 'Utilisateur courant avec ses rôles et sites accessibles.',
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer', 'example': 12},
                    'login': {'type': 'string', 'example': 'jdoe'},
                    'roles': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'example': ['user', 'admin']
                    },
                    'sites': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer', 'example': 1},
                                'name': {'type': 'string', 'example': 'Site A'}
                            }
                        }
                    }
                }
            }
        },
        '401': {
            'description': 'Unauthorized',
            'schema': {'type': 'object', 'properties': {'error': {'type': 'string', 'example': 'unauthorized'}}}
        }
    }
})
def me_root():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    role_names = []
    seen_roles = set()
    sites_dict = {}
    for assoc in user.user_site_roles.all():
        if assoc.role and assoc.role.name not in seen_roles:
            seen_roles.add(assoc.role.name)
            role_names.append(assoc.role.name)
        if assoc.site:
            sid = assoc.site.id
            if sid not in sites_dict:
                sites_dict[sid] = {'id': assoc.site.id, 'name': assoc.site.name}

    return jsonify({
        'id': user.id,
        'login': user.login,
        'roles': role_names,
        'sites': list(sites_dict.values())
    }), 200
