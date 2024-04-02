# JobRoute.py

from flask import Flask
from flask_restx import Api, Resource, fields
from pymongo import MongoClient

from app import api, mongo
from app.Controllers.JobController import JobController

# Instantiate the controller
job_controller = JobController(mongo)

# Define the Swagger model for a job
# This is a hypothetical workaround and not standard usage for Flask-RESTx
job_model = api.model('Job', {
    'jobTitle': fields.String(required=True, description='Job Title'),
    'description': fields.String(required=True, description='Job Description'),
    'company_information': fields.String(required=True, description='Company Information'),
    'location': fields.String(required=True, description='Location'),
    'employment_type': fields.String(required=True, description='Employment Type'),
    'salary_compensation': fields.String(required=True, description='Salary and Compensation'),
    # This is illustrative and not directly supported as per Flask-RESTx documentation.
    'requirements': fields.List(fields.String, required=True, description='List of Job Skills'),
    'created_at': fields.DateTime(description='Date and Time of Job Creation', required=False, readonly=True),
    'end_date': fields.DateTime(required=True, description='End Date of the Job'),
})


# Define the routes
@api.route('/jobs')
class JobsResource(Resource):
    def get(self):
        return job_controller.get_all_jobs()

    @api.expect(job_model)
    def post(self):
        return job_controller.create_job()


@api.route('/jobs/<string:job_id>')  # Use string:job_id to specify that job_id is a string
class JobResource(Resource):
    def get(self, job_id):
        return job_controller.get_job_by_id(job_id)

    @api.expect(job_model)
    def put(self, job_id):
        return job_controller.update_job(job_id)

    def delete(self, job_id):
        return job_controller.delete_job(job_id)
