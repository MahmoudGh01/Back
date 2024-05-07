from bson import ObjectId
from datetime import datetime


class FileModel:
    def __init__(self, db):
        self.collection = db['Files']

    def create_File(self, data):
        # Generate a new ObjectId for the _id field
        # data['_id'] = str(ObjectId())
        data['created_at'] = datetime.utcnow()
        return self.collection.insert_one(data).inserted_id

    def get_all_Files(self):
        return list(self.collection.find())

    def get_File_by_id(self, File_id):
        File = self.collection.find_one({'_id': ObjectId(File_id)})
        if File:
            File['_id'] = str(File['_id'])
        return File

    def get_files_by_user_id(self, user_id):
        try:
            files = list(self.collection.find({'user_id': ObjectId(user_id)}))
            for file in files:
                file['_id'] = str(file['_id'])
            return files
        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def update_File(self, File_id, data):
        # Exclude the '_id' field from the update
        File = self.collection.update_one({'_id': File_id}, {'$set': {k: v for k, v in data.items() if k != '_id'}})
        return File

    def delete_File(self, File_id):
        File = self.collection.delete_one({'_id': File_id})

        return File
