import base64
import os

from bson import ObjectId
from flask_cors import CORS

from app import app, mongo
from flask import Flask, request, jsonify, Response
from flask_pymongo import PyMongo, MongoClient

from app.Controllers.JobController import JobController

client = MongoClient(app.config['MONGO_URI'], tlsAllowInvalidCertificates=True)  # Establish connection to MongoDB
db = client['db']  # Use your database name
collection = db['job_applications']  # Use your collection name

# Instantiate the controller
job_controller = JobController(mongo)

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


@app.route('/job-applications', methods=['GET'])
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
@app.route('/job-application/<job_application_id>', methods=['PUT'])
def update_job_application_status(job_application_id):
    # Update the status of the specified job application
    new_status = request.json.get('status')
    update_job_application_status_in_database(job_application_id, new_status)
    return jsonify({'message': 'Job application status updated successfully'})


@app.route('/apply-for-job', methods=['POST'])
def apply_for_job():
    # Retrieve job application data from request
    user_id = request.headers.get('user_id')
    job_application_data = request.json

    # Extract user skills from job application data
    user_skills = job_application_data.get('skills')

    # Retrieve job requirements from database based on job ID
    job_id = job_application_data.get('job_id')
    job = job_controller.get_job_by_id(job_id)

    job_requirements = job['requirements']

    # Calculate fit score based on user skills and job requirements
    fit_score = calculate_fit_score(user_skills, job_requirements)

    # Process job application (save to database, calculate fit score, etc.)

    return jsonify({'fit_score': fit_score})


@app.route('/save-application', methods=['POST'])
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


def calculate_fit_score(user_skills, job_requirements):
    if not job_requirements:
        return 0  # Return 0 if no job requirements are specified

    common_skills = set(user_skills) & set(job_requirements)
    fit_score = (len(common_skills) / len(job_requirements)) * 100
    return fit_score



CORS(app)
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=10000)
