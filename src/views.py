from flask import request, send_from_directory, session
from flask_restx import marshal, Resource
from werkzeug.utils import secure_filename

from app import app, api
from ad_insertion_executor import ProcessingExecutor, InsertionExecutor
from flask import request
from flask_restx import marshal, Resource

from app import app, api
from src import serializers
from ad_insertion_executor import ProcessingExecutor, InsertionExecutor


@api.route('/conf')
class ConfigurationResource(Resource):
    @staticmethod
    def get() -> dict:
        """ Get Current Model Configuration """

        return marshal(app.config['model_config'], serializers.conf_serializer)

    @api.expect(serializers.conf_serializer)
    def put(self) -> dict:
        """ Update Model Configuration """

        app.config['model_config'].update(request.get_json())
        app.save_conf()
        return marshal(app.config['model_config'], serializers.conf_serializer)


@api.route('/processing')
class ProcessingResource(Resource):

    @api.expect(serializers.processing_serializer)
    def post(self):
        """ Video Processing """

        payload = request.get_json()
        session['video'] = payload['video']
        session['logo'] = payload['logo']
        processing_executor = ProcessingExecutor(payload['video'], payload['logo'], app.conf_path)
        message = processing_executor.process_video()
        # message = process_video(payload['video'], payload['logo'], app.conf_path)
        return message

    @staticmethod
    def get() -> dict:
        """ Advertisement Insertion """
        insertion_executor = InsertionExecutor(session['video'], session['logo'], app.conf_path)
        message = insertion_executor.insert_ads()
        # message = insert_ads(session['video'], session['logo'], app.conf_path)
        return message
