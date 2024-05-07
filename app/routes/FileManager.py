import os

from flask import jsonify, send_from_directory, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Resource, fields, Namespace
from werkzeug.utils import secure_filename

from app import api, app, mongo
from app.Controllers.FileController import FileController
from config import Config

ALLOWED_EXTENSIONS = {'pdf', 'mp4', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Instantiate the controller
file_controller = FileController(mongo)

# Define the file model for documentation purposes
file_model = api.model('File', {
    'user_id': fields.String(required=True, description='User ID'),
    'files': fields.List(fields.String, required=True, description='List of Files'),
    'created_at': fields.DateTime(description='Date and Time of File Creation', required=False, readonly=True),
})

# Namespace for the API
file_ns = Namespace('Files', description='Operations related to file management')


# Define the routes
@file_ns.route('/')
class FilesResource(Resource):
    def get(self):
        """Get all files"""
        return file_controller.get_all_files()

    @file_ns.expect(file_model)
    def post(self):
        """Create a new file"""
        return file_controller.create_file()


@file_ns.route('/<string:file_id>')
class FileResource(Resource):
    def get(self, file_id):
        """Get a file by its ID"""
        return file_controller.get_file_by_id(file_id)

    @file_ns.expect(file_model)
    def put(self, file_id):
        """Update a file by its ID"""
        return file_controller.update_file(file_id)

    def delete(self, file_id):
        """Delete a file by its ID"""
        return file_controller.delete_file(file_id)


# JWT-protected file upload and association with user
@file_ns.route('/upload')
class UploadFile(Resource):
    @jwt_required()
    def post(self):
        """Upload a file and associate it with the current user"""
        current_user = get_jwt_identity()

        if 'resume' not in request.files:
            return {'message': 'No file part'}, 401

        file = request.files['resume']
        if file.filename == '':
            return {'message': 'No selected file'}, 402

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(file_path)
            print("Uploaded to: " + file_path)

            # Save file information to the database
            file_id = file_controller.add_file(current_user, filename)

            return jsonify({"message": "File uploaded", "file_id": file_id}), 200
        else:
            return jsonify({'error': 'File not allowed'}), 400


# Get files associated with a particular user
@file_ns.route('/user/<string:user_id>')
class FilesByUser(Resource):
    def get(self, user_id):
        """Get files by user ID"""
        return file_controller.get_all_files_by_user_id(user_id)


# Retrieve all uploaded files (without user filtering)
@file_ns.route('/all', methods=['GET'])
class GetFiles(Resource):
    def get(self):
        """Get a list of all uploaded files"""
        files = []
        for filename in os.listdir(Config.UPLOAD_FOLDER):
            path = os.path.join(Config.UPLOAD_FOLDER, filename)
            print("Fetched files from: " + path)
            if os.path.isfile(path):
                files.append(filename)

        return jsonify(files)


# Download a specific file
@file_ns.route('/download', methods=['GET'])
class GetFile(Resource):
    def get(self):
        """Download a specific file by filename"""
        filename = request.args.get('filename')

        if not filename:
            return {'message': 'No filename provided'}, 400

        safe_filename = secure_filename(filename)
        try:
            return send_from_directory(directory=Config.UPLOAD_FOLDER, path=safe_filename, as_attachment=True)
        except FileNotFoundError:
            return {'message': 'No file found'}, 404


# Add the namespace to the API
api.add_namespace(file_ns)
