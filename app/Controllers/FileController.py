from bson import ObjectId
from datetime import datetime

from flask import request


class FileController:
    def __init__(self, mongo):
        self.collection = mongo.db.files

    def get_all_files(self):
        """Get all files"""
        files = list(self.collection.find())
        for file in files:
            file['_id'] = str(file['_id'])
            file['user_id'] = str(file['user_id'])
        return files

    def get_all_files_by_user_id(self, user_id):
        """Get files by user ID"""
        try:
            files = list(self.collection.find({'user_id': ObjectId(user_id)}))
            for file in files:
                file['_id'] = str(file['_id'])
                file['user_id'] = str(file['user_id'])
            return files
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def get_file_by_id(self, file_id):
        """Get a file by its ID"""
        try:
            file = self.collection.find_one({'_id': ObjectId(file_id)})
            if file:
                file['_id'] = str(file['_id'])
                file['user_id'] = str(file['user_id'])
                return file
            return {'message': 'File not found'}, 404
        except Exception as e:
            print(f"An error occurred: {e}")
            return {'message': 'An error occurred'}, 500

    def create_file(self):
        """Create a new file"""
        data = request.get_json()
        user_id = data.get('user_id')
        files = data.get('files')
        created_at = datetime.utcnow()

        try:
            file_id = self.collection.insert_one({
                'user_id': ObjectId(user_id),
                'files': files,
                'created_at': created_at
            }).inserted_id
            return {'message': 'File created', 'file_id': str(file_id)}, 201
        except Exception as e:
            print(f"An error occurred: {e}")
            return {'message': 'An error occurred'}, 500

    def update_file(self, file_id):
        """Update a file by its ID"""
        data = request.get_json()
        user_id = data.get('user_id')
        files = data.get('files')

        try:
            result = self.collection.update_one(
                {'_id': ObjectId(file_id)},
                {'$set': {
                    'user_id': ObjectId(user_id),
                    'files': files
                }}
            )
            if result.matched_count:
                return {'message': 'File updated'}
            return {'message': 'File not found'}, 404
        except Exception as e:
            print(f"An error occurred: {e}")
            return {'message': 'An error occurred'}, 500

    def delete_file(self, file_id):
        """Delete a file by its ID"""
        try:
            result = self.collection.delete_one({'_id': ObjectId(file_id)})
            if result.deleted_count:
                return {'message': 'File deleted'}
            return {'message': 'File not found'}, 404
        except Exception as e:
            print(f"An error occurred: {e}")
            return {'message': 'An error occurred'}, 500

    def add_file(self, user_id, filename):
        """Add a new file to a user"""
        created_at = datetime.utcnow()

        try:
            file_id = self.collection.insert_one({
                'user_id': ObjectId(user_id),
                'filename': filename,
                'created_at': created_at
            }).inserted_id
            return str(file_id)
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
