# JobModel.py

from pymongo import MongoClient
from bson import ObjectId


class JobModel:
    def __init__(self, db):
        self.collection = db['Jobs']

    def create_job(self, data):
        # Generate a new ObjectId for the _id field
        data['_id'] = str(ObjectId())
        return self.collection.insert_one(data).inserted_id

    def get_all_jobs(self):
        return list(self.collection.find())

    def get_job_by_id(self, job_id):
        return self.collection.find_one({'_id': job_id})

    def update_job(self, job_id, data):
        # Exclude the '_id' field from the update
        return self.collection.update_one({'_id': job_id}, {'$set': {k: v for k, v in data.items() if k != '_id'}})

    def delete_job(self, job_id):
        return self.collection.delete_one({'_id': job_id})
