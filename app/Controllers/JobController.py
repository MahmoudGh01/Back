# JobController.py
import datetime

from flask import request
from bson import ObjectId
from app.Models.JobModel import JobModel


class JobController:
    def __init__(self, db):
        self.model = JobModel(db.db)

    def create_job(self):
        data = request.get_json()
        job_id = self.model.create_job(data)
        return {'job_id': str(job_id)}

    def get_all_jobs(self):
        jobs = self.model.collection.find()
        serialized_jobs = []
        for job in jobs:
            job['_id'] = str(job['_id'])  # Convert ObjectId to string
            for key, value in job.items():
                if isinstance(value, datetime.datetime):
                    job[key] = value.isoformat()  # Convert datetime to ISO format string
            serialized_jobs.append(job)
        return serialized_jobs

    def get_job_by_id(self, job_id):
        job = self.model.get_job_by_id(job_id)
        if job:
            job['_id'] = str(job['_id'])  # Convert ObjectId to string
            for key, value in job.items():
                if isinstance(value, datetime.datetime):
                    job[key] = value.isoformat()  # Convert datetime to ISO format string
            return job
        else:
            return {'error': 'Job not found'}

    def update_job(self, job_id):
        data = request.get_json()
        result = self.model.update_job(ObjectId(job_id), data)
        return {'modified_count': result.modified_count}

    def delete_job(self, job_id):
        result = self.model.delete_job(ObjectId(job_id))
        return {'deleted_count': result.deleted_count}
