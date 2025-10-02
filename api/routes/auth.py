from flask import Blueprint, request, jsonify, redirect, url_for, render_template, current_app
from flask_login import login_user, logout_user, login_required
from flasgger import swag_from
from models import User, db
import jwt
import datetime

auth_bp = Blueprint('auth', __name__)

# Helper to get current user from Authorization: Bearer <token>
def _get_current_user():
    try:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        token = auth_header.split(' ', 1)[1]
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'default_secret_key')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if not user_id:
            return None
        return User.query.get(user_id)
    except Exception:
        return None

@auth_bp.route('/me', methods=['GET'])
@swag_from({
    'tags': ['Authentication'],
    'description': 'Obtenir l\'utilisateur courant (route sous /auth). Nécessite un header Authorization: Bearer <token>.',
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
def me():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    # Collect unique role names across global and site-specific roles
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

@auth_bp.route('/login', methods=['POST', 'OPTIONS'])
@swag_from({
    'tags': ['Authentication'],
    'description': 'Connexion de l\'utilisateur via JSON. Fournissez "login" et "password" dans le corps de la requête.',
    'consumes': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['login', 'password'],
                'properties': {
                    'login': {'type': 'string', 'example': 'monlogin'},
                    'password': {'type': 'string', 'example': 'monmotdepasse'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Utilisateur connecté avec succès',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Connecté'},
                    'user_id': {'type': 'integer', 'example': 1},
                    'sites': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer', 'example': 3},
                                'name': {'type': 'string', 'example': 'Site A'},
                                'roles': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'object',
                                        'properties': {
                                            'id': {'type': 'integer', 'example': 2},
                                            'name': {'type': 'string', 'example': 'admin'}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    'global_roles': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer', 'example': 1},
                                'name': {'type': 'string', 'example': 'super_admin'}
                            }
                        },
                        'description': 'Rôles globaux de l\'utilisateur (non liés à un site spécifique)'
                    },
                    'token': {'type': 'string', 'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...', 'description': 'JWT token d\'authentification'}
                }
            }
        },
        '401': {
            'description': 'Identifiants invalides',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string', 'example': 'Identifiants invalides'}
                }
            }
        }
    }
})
def login():
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    if not data or 'login' not in data or 'password' not in data:
        return jsonify({'error': 'Les champs "login" et "password" sont requis'}), 400

    login_input = data.get('login')
    password = data.get('password')
    user = User.query.filter_by(login=login_input).first()
    if user and user.check_password(password):
        login_user(user)  # L'utilisateur est connecté et stocké dans la session

        # Récupérer la liste des associations via le backref user_site_roles
        # et grouper par site avec leurs rôles associés.
        sites_dict = {}
        global_roles = []

        for assoc in user.user_site_roles.all():
            # Traiter les rôles globaux (sans site)
            if assoc.site_id is None:
                if assoc.role and assoc.role.id not in [r['id'] for r in global_roles]:
                    global_roles.append({
                        'id': assoc.role.id,
                        'name': assoc.role.name
                    })
            # Traiter les rôles liés à un site
            elif assoc.site:
                sid = assoc.site.id
                if sid not in sites_dict:
                    sites_dict[sid] = {
                        'id': assoc.site.id,
                        'name': assoc.site.name,
                        'roles': []
                    }
                if assoc.role:
                    # Ajoute le rôle s'il n'est pas déjà présent
                    if assoc.role.id not in [r['id'] for r in sites_dict[sid]['roles']]:
                        sites_dict[sid]['roles'].append({
                            'id': assoc.role.id,
                            'name': assoc.role.name
                        })

        # Générer un token JWT
        token_payload = {
            'user_id': user.id,
            'login': user.login,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)  # Expiration dans 1 jour
        }

        # Utiliser une clé secrète depuis la configuration de l'application ou une valeur par défaut
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'default_secret_key')
        token = jwt.encode(token_payload, secret_key, algorithm='HS256')

        response = {
            'message': 'Connecté',
            'user_id': user.id,
            'sites': list(sites_dict.values()),
            'token': token
        }

        # Ajouter les rôles globaux à la réponse s'il y en a
        if global_roles:
            response['global_roles'] = global_roles

        return jsonify(response), 200
    else:
        return jsonify({'error': 'Identifiants invalides'}), 401

@auth_bp.route('/logout', methods=['POST', 'OPTIONS', 'GET'])
@swag_from({
    'tags': ['Authentication'],
    'description': 'Déconnecte l\'utilisateur connecté.',
    'responses': {
        '200': {
            'description': 'Utilisateur déconnecté avec succès',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Déconnecté'}
                }
            }
        }
    }
})
def logout():
    # CORS preflight
    if request.method == 'OPTIONS':
        return '', 200

    # Support stateless JWT-first clients: accept Bearer token but we just return success.
    # If a Flask-Login session exists, we clear it; otherwise, still return 200 to be idempotent.
    try:
        logout_user()
    except Exception:
        pass
    return jsonify({'message': 'Déconnecté'}), 200
