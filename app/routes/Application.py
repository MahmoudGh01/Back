import base64
import os

from bson import ObjectId

from app import app, mongo, api
from flask import Flask, request, jsonify, Response
from flask_pymongo import PyMongo, MongoClient

client = MongoClient('mongodb://localhost:27017/')  # Establish connection to MongoDB
db = client['AiRecruit']  # Use your database name
collection = db['job_applications']  # Use your collection name




def get_current_user_id():
    """
    Retrieve the ID of the currently logged-in user from the request headers.
    This function assumes that the user ID is included in the request headers
    after successful authentication.
    """
    # Example: Extract user ID from the request headers
    user_id = request.headers.get('user_id')

    # You might need additional logic here to extract the user ID based on your authentication mechanism

    return user_id


@api.route('/job-applications', methods=['GET'])
def get_job_applications():
    # Retrieve job applications for the logged-in user
    user_id = get_current_user_id()  # Implement this function to get the user ID
    job_applications = get_job_applications_for_user(user_id)

    # Check if the response is already a Flask Response object
    if isinstance(job_applications, Response):
        return job_applications

    # If not, jsonify the data and return
    return jsonify(job_applications)
# Endpoint to update job application status
@api.route('/job-application/<job_application_id>', methods=['PUT'])
def update_job_application_status(job_application_id):
    # Update the status of the specified job application
    new_status = request.json.get('status')
    update_job_application_status_in_database(job_application_id, new_status)
    return jsonify({'message': 'Job application status updated successfully'})


def get_job_requirements(job_id):
    try:
        # Assuming you have a MongoDB collection named 'jobs' where each document represents a job posting
        job = db.jobs.find_one({'_id': ObjectId(job_id)})
        if job:
            return job.get('requirements', [])  # Assuming 'requirements' is a field in your job document
        else:
            return []  # If job not found or no requirements specified, return an empty list
    except Exception as e:
        print(f"Error retrieving job requirements: {e}")
        return []  # Return empty list on error


@app.route('/apply-for-job', methods=['POST'])
def apply_for_job():
    # Retrieve job application data from request
    user_id = request.headers.get('user_id')
    job_application_data = request.json

    # Extract user skills from job application data
    user_skills = job_application_data.get('skills')

    # Retrieve job requirements from database based on job ID
    job_id = job_application_data.get('job_id')
    job_requirements = get_job_requirements(job_id)

    # Calculate fit score based on user skills and job requirements
    fit_score = calculate_fit_score(user_skills, job_requirements)

    # Process job application (save to database, calculate fit score, etc.)

    return jsonify({'fit_score': fit_score})


@api.route('/save-application', methods=['POST'])
def save_application():
    try:
        data = request.form

        new_application = {
            'firstName': data.get('firstName'),
            'lastName': data.get('lastName'),
            'email': data.get('email'),
            'coverLetter': data.get('coverLetter'),
            'job_id': data.get('job_id')  # Add job_id
        }

        # Save uploaded file
        cvPdf = request.files['cvPdf']
        filename = os.path.join(app.config['UPLOAD_FOLDER'], cvPdf.filename)
        cvPdf.save(filename)

        # Convert filename to string before storing
        new_application['cvPdf'] = str(filename)

        collection.insert_one(new_application)

        return jsonify({'message': 'Application form data saved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# Assuming you have a MongoDB collection named 'job_applications'
# where each document represents a job application

def get_job_applications_for_user(user_id):
    """
    Retrieve job applications for a specific user from the database.
    """
    try:
        # Example query to retrieve job applications for a user from MongoDB
        job_applications = list(collection.find({'user_id': user_id}))

        # Convert ObjectId to string for JSON serialization
        for application in job_applications:
            application['_id'] = str(application['_id'])

        return job_applications  # Return a serializable data structure
    except Exception as e:
        return {'error': str(e)}, 500

def update_job_application_status_in_database(job_application_id, new_status):
    """
    Update the status of a job application in the database.
    """
    try:
        # Example query to update job application status in MongoDB
        collection.update_one(
            {'_id': ObjectId(job_application_id)},
            {'$set': {'status': new_status}}
        )

        return jsonify({'message': 'Job application status updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

from flask import request

from flask import request

@api.route('/jobs', methods=['POST'])
def create_job():
    try:
        # Parse the incoming request to get the job details
        job_data = request.json
        job_description = job_data.get('description')
        job_title = job_data.get('jobTitle')
        job_location = job_data.get('location')
        job_requirements = job_data.get('requirements')  # Add requirements

        # Insert the job details into the database
        job_id = mongo.db.jobs.insert_one({
            'description': job_description,
            'jobTitle': job_title,
            'location': job_location,
            'requirements': job_requirements,  # Insert requirements
        }).inserted_id

        return jsonify({'message': 'Job created successfully', 'job_id': str(job_id)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_fit_score(user_skills, job_requirements):
    if not job_requirements:
        return 0  # Return 0 if no job requirements are specified

    common_skills = set(user_skills) & set(job_requirements)
    fit_score = (len(common_skills) / len(job_requirements)) * 100
    return fit_score
@api.route('/jobs/<job_id>', methods=['GET'])
def get_job_details(job_id):
    try:
        job = mongo.db.jobs.find_one({'_id': ObjectId(job_id)})
        if job:
            # Convert ObjectId to string before returning
            job['_id'] = str(job['_id'])
            return jsonify(job), 200
        else:
            return jsonify({'error': 'Job not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

