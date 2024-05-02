from flask import request, send_from_directory
from flask_restx import Resource
from werkzeug.utils import secure_filename


from app import api, app


@api.route('/video', methods=['GET'])
class GetVideo(Resource):
    def get(self):
        # Use query parameters instead of JSON body
        filename = request.args.get('video_name')

        if not filename:
            return {'message': 'No filename provided'}, 401

        safe_filename = secure_filename(filename)
        try:
            return send_from_directory(directory=app.config['UPLOAD_FOLDER'], path=safe_filename, as_attachment=True)
        except FileNotFoundError:
            # Using 404 is more appropriate here as it indicates "Not Found"
            return {'message': 'No file found'}, 404
