import os

from flask import jsonify, send_from_directory, abort, request
from flask_restx import Resource
from werkzeug.utils import secure_filename

from app import api, app

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

upload_parser = api.parser()
upload_parser.add_argument('resume', location='files', type='FileStorage', required=True)


@api.route('/upload')
class UploadFile(Resource):
    def post(self):
        if 'resume' not in request.files:
            return {'message': 'No file part'}, 401

        file = request.files['resume']
        if file.filename == '':
            return {'message': 'No selected file'}, 402

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print("Uploaded to : "+file_path)

            # You could add additional processing here, such as generating a file preview

            return 200
        else:
            return jsonify({'error': 'File not allowed'}), 400


@api.route('/files', methods=['GET'])
class GetFiles(Resource):
    def get(self):
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print("Fetched files from: "+path)
            if os.path.isfile(path):
                files.append(filename)

        return jsonify(files)


@api.route('/file', methods=['GET'])
class GetFile(Resource):
    def get(self):
        # Use query parameters instead of JSON body
        filename = request.args.get('filename')

        if not filename:
            return {'message': 'No filename provided'}, 400

        safe_filename = secure_filename(filename)
        try:
            return send_from_directory(app.config['UPLOAD_FOLDER'], safe_filename, as_attachment=True)
        except FileNotFoundError:
            # Using 404 is more appropriate here as it indicates "Not Found"
            abort(404)