from flask import Flask
from redis import Redis
from werkzeug.utils import import_string

redis = Redis(decode_responses=True)

blueprints = [
    'app.routes:bp',
]


def create_app(config_name=None):
    app = Flask(__name__)
    for name in blueprints:
        blueprint = import_string(name)
        app.register_blueprint(blueprint)

    return app
