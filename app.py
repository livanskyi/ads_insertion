import yaml

from flask import Flask
from flask_restx import Api

from pathlib import Path

from src import settings


class AdvApp(Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.root_path = Path.cwd()

        self.conf_path = self.root_path / settings.conf_path
        self.default_conf_path = self.root_path / settings.default_conf_path

        self.config['model_config'] = self.load_conf()

    def load_conf(self) -> dict:
        path = self.default_conf_path if not self.conf_path.is_file() else self.conf_path

        with open(path) as file:
            return yaml.load(file, Loader=yaml.FullLoader)

    def save_conf(self) -> None:
        with open(self.conf_path, 'w') as file:
            return yaml.dump(self.config['model_config'], file)


app = AdvApp(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
api = Api(app, title='Advertisement REST API', validate=True)

from src.views import *

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
