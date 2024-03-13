import base64
import datetime
from sched import scheduler

import schedule
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS
import os

from pyfcm import FCMNotification
from sentence_transformers import SentenceTransformer
from pdfminer.high_level import extract_text
from bson import ObjectId
# from werkzeug.utils import secure_filename
import numpy as np
from transformers import pipeline

from app import app, mongo
from flask import Flask, request, jsonify, Response, current_app
from flask_pymongo import PyMongo, MongoClient
import spacy

from app.Controllers.auth import send_email, send_accept_email, send_refusal_email1
from app.Repository import UserRepo
from app.Repository.UserRepo import UserRepository
from app.routes.JobRoute import job_controller

db = mongo.db  # Use your database name
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


def get_job_requirements(job_id):
    try:
        # Assuming you have a MongoDB collection named 'jobs' where each document represents a job posting
        job = db.Jobs.find_one({'_id': ObjectId(job_id)})
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
    job = job_controller.get_job_by_id(job_id)

    job_requirements = job['requirements']
    # Calculate fit score based on user skills and job requirements
    fit_score = calculate_fit_score(user_skills, job_requirements)

    # Process job application (save to database, calculate fit score, etc.)
    return jsonify({'fit_score': fit_score})


# pdf to txt
def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a given PDF file using PDFMiner.
    """
    return extract_text(pdf_path)


nlp = spacy.load("en_core_web_sm")


# IA Analyze cv
def analyze_skills_with_spacy(cv_text, job_description):
    # Create spaCy Doc objects for the CV text and the concatenated job description
    cv_doc = nlp(cv_text.lower())
    job_desc_doc = nlp(' '.join(job_description).lower())

    # Calculate the similarity between the CV and job description using spaCy's built-in method
    similarity = cv_doc.similarity(job_desc_doc)

    # Convert the similarity to a percentage score
    percentage_score = similarity * 100

    return percentage_score


# Load a pre-trained English model
nlp = spacy.load("en_core_web_sm")
# Load a pre-trained sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')


# IA Analyze Skills User
def analyze_skills_with_ai_enhanced(user_skills, job_required_skills, model, threshold):
    score = 0
    total_skills = len(job_required_skills)

    # Create embeddings for user skills and job required skills
    user_skills_embeddings = model.encode(user_skills)
    job_skills_embeddings = model.encode(job_required_skills)

    # Compute cosine similarity between user skills and job required skills
    similarity_matrix = np.inner(user_skills_embeddings, job_skills_embeddings)

    # Count matches based on a threshold
    for user_skill_similarities in similarity_matrix:
        if max(user_skill_similarities) > threshold:  # Adjust the threshold as needed
            score += 1

    # Calculate percentage
    if total_skills > 0:
        percentage_score = (score / total_skills) * 100
    else:
        percentage_score = 0  # Avoid division by zero if there are no skills listed

    return percentage_score


# IA Analyze Cover Letter
def analyze_cover_letter_transformers(cover_letter):
    """
    Analyzes the cover letter using a pre-trained sentiment analysis model
    and returns a score.
    """
    # Load a pre-trained sentiment analysis pipeline
    sentiment_pipeline = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

    # Analyze the cover letter
    result = sentiment_pipeline(cover_letter)

    # Convert the result to a score
    if result[0]['label'] == 'POSITIVE':
        score = result[0]['score'] * 100  # Scale to 0-100
    else:
        score = (1 - result[0]['score']) * 100  # Invert and scale for negative sentiment
    return score


# save application and add scores
@app.route('/save-application', methods=['POST'])
def save_application():
    try:
        data = request.form

        new_application = {

            'userID': data.get('userId'),

            'coverLetter': data.get('coverLetter'),
            'status': 'on hold',  # Default status
            'job_id': data.get('job_id')  # Add job_id
        }
        print(data.get('userId'))
        # Save uploaded file
        cvPdf = request.files['cvPdf']
        filename = os.path.join(app.config['UPLOAD_FOLDER'], cvPdf.filename)
        cvPdf.save(filename)

        # Convert filename to string before storing
        new_application['cvPdf'] = str(filename)
        user_id = ObjectId(data.get('userId'))
        user = UserRepo.UserRepository.get_by_id(mongo, user_id)

        print(user)
        user_skills = user['skills']
        print(user_skills)
        job = job_controller.get_job_by_id(new_application['job_id'])

        # Dynamically determine the required skills, here as an example
        required_skills = job.get('requirements', [])
        model = SentenceTransformer('all-MiniLM-L6-v2')

        # Calculate individual scores
        score_cv = analyze_skills_with_spacy(extract_text_from_pdf(filename), required_skills)
        score_skills = analyze_skills_with_ai_enhanced(user_skills, required_skills, model, 0.7)
        score_cover_letter = analyze_cover_letter_transformers(new_application['coverLetter'])

        # Calculate the final score as an average of individual scores
        final_score = (score_cv + score_skills + score_cover_letter) / 3

        # Convert filename to string before storing
        new_application['cvPdf'] = str(filename)
        new_application['score_cv'] = score_cv
        new_application['score_skills'] = score_skills
        new_application['score_cover_letter'] = score_cover_letter
        new_application['final_score'] = final_score

        # Check the final score and update status accordingly
        if final_score < 15:
            new_application['status'] = 'refused'
            send_refusal_email(user['email'],
                               f"{user['name']} ")
            response_message = 'Application form data saved successfully with status refused.'
        else:
            response_message = 'Application form data saved successfully.'

        # Insert the application document into the database
        collection.insert_one(new_application)

        return jsonify({'message': response_message}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Assuming you have a MongoDB collection named 'job_applications'
# where each document represents a job application
def fetch_applications(job_id):
    # Connect to your database
    db = mongo.db  # Assuming you're using MongoDB with Flask-PyMongo

    # Query the database for applications associated with the given job ID
    applications = db.applications.find({'job_id': job_id})

    # Convert the MongoDB cursor to a list of dictionaries
    application_list = [app for app in applications]

    return application_list


def update_application_status(application_id, new_status):
    # Connect to your database
    # Assuming you're using MongoDB with Flask-PyMongo

    # Update the status of the application with the given application ID
    result = collection.update_one(
        {'_id': application_id},
        {'$set': {'status': new_status}}
    )

    # Check if the update was successful
    if result.matched_count == 0:
        print(f"No application found with ID {application_id}")
    elif result.modified_count == 0:
        print(f"Application with ID {application_id} was already in status {new_status}")
    else:
        print(f"Application with ID {application_id} has been updated to status {new_status}")


# Eliminate 80% and send mail to accepte to 20% and send mail refuse to 80%
def evaluate_job_applications(job_id, threshold=0.7):
    # Fetch all applications for the given job_id
    applications = fetch_applications(job_id)

    # Analyze and score each application
    scored_applications = []
    for app in applications:
        cv_text = extract_text_from_pdf(app['cv_pdf_path'])
        cv_score = analyze_skills_with_spacy(cv_text, app['job_required_skills'])
        skills_score = analyze_skills_with_ai_enhanced(app['user_skills'], app['job_required_skills'], model, threshold)
        cover_letter_score = analyze_cover_letter_transformers(app['cover_letter'])

        # Combine scores (example: simple average)
        final_score = (cv_score + skills_score + cover_letter_score) / 3
        scored_applications.append((app['email'], final_score))

    # Sort applications by score in descending order
    scored_applications.sort(key=lambda x: x[1], reverse=True)

    # Determine the index for the top 20% of applications
    top_20_percent_index = len(scored_applications) * 20 // 100

    # Process the top 20% of applications
    for app, score in scored_applications[:top_20_percent_index]:
        send_acceptance_email(app['email'], f"{app['firstName']} {app['lastName']}")
        update_application_status(app['id'],
                                  'accepted')  # Assuming a function to update the application status in the database

    # Process the bottom 80% of applications
    for app, score in scored_applications[top_20_percent_index:]:
        send_refusal_email(app['email'], f"{app['firstName']} {app['lastName']}")
        update_application_status(app['id'],
                                  'refused')  # Assuming a function to update the application status in the database

    return [app for app, score in scored_applications[:top_20_percent_index]]


def fetch_job_ids_from_applications():
    # Fetch all job applications
    db = mongo.db  # Assuming you're using MongoDB with Flask-PyMongo

    applications = db.applications.find()

    # Extract unique job_ids
    job_ids = set()
    for app in applications:
        job_ids.add(app['job_id'])

    return list(job_ids)


scheduler = BackgroundScheduler()


# Initialize FCM with your Firebase server key
# push_service = FCMNotification(api_key="AAAAj9DbS5U:APA91bHaXdD_iUoV7KFEWRgrtt3kE1RFjl0ahdlRzSVPUa-nVyzqerOrqlefuS_k9qlJqBMV1wTCUem8G7c5a9OTz44j0IG1pMwENIQjN6DoSn5iH5eZYsp4eATjCP7LKKQAbBrPOBXF")

# def send_push_notification(tokens, title, message):
#     result = push_service.notify_multiple_devices(
#         registration_ids=tokens,
#         message_title=title,
#         message_body=message
#     )
#     return result

def scheduled_evaluation():
    applications_cursor = db.job_applications.find()

    # Create a set to store unique job IDs
    job_ids = set()

    # Iterate over the cursor to extract job IDs and add them to the set
    for app in applications_cursor:
        job_ids.add(app.get('job_id'))

    print(f"Unique Job IDs: {job_ids}")

    for job_id in job_ids:
        applications_for_job = list(collection.find({'job_id': job_id}))
        print(f"Applications for job {job_id}: {applications_for_job}")

        # Analyze and score each application
        scored_applications = []
        for s in applications_for_job:
            # Assuming 'final_score' is correctly calculated and stored in each app document
            final_score = s.get('final_score')
            userId = s.get('userId')
            print(f"final_score:{final_score}")
            scored_applications.append((s, final_score))

        print(f"Scored applications: {scored_applications}")

        # Sort applications by score in descending order
        scored_applications.sort(key=lambda x: x[1], reverse=True)

        # Determine the index for the top 20% of applications
        top_20_percent_index = len(scored_applications) * 20 // 100
        print(f"top 20:{top_20_percent_index}")

        # Process the top 20% of applications
        for app, score in scored_applications[:top_20_percent_index]:
            print(f"id: {app.get('_id')}")
            # send_acceptance_email(app.get('email'),f"{app.get('firstName')} {app.get('lastName')}")
            collection.update_one(
                {'_id': ObjectId(app.get('_id'))},
                {'$set': {'status': 'accepted'}}
            )
            print(f"Accepted: {app['email']} with final score {score} STATUS :{app.get('status')}")

        # Process the bottom 80% of applications
        for y, score in scored_applications[top_20_percent_index:]:

            send_refusal_email(y.get('email'), f"{y.get('firstName')} {y.get('lastName')}")
            collection.update_one(
                {'_id': ObjectId(y.get('_id'))},
                {'$set': {'status': 'refused'}}
            )
            update_application_status(y.get('_id'), 'refused')
            print(f"Refused: {y.get('email')} with final score {score} STATUS :{y.get('status')}")

    # Send a push notification to notify that the evaluation has been completed
    # device_tokens = ["DEVICE_TOKEN_1", "DEVICE_TOKEN_2"]  # Replace with actual device tokens
    # send_push_notification(
    #     tokens=device_tokens,
    #     title="Job Application Update",
    #     message="The job application evaluation has been completed."
    # )


# Schedule the evaluation function to run at a specific date and time
scheduler.add_job(scheduled_evaluation, 'date', run_date='2024-03-12 22:16:00')

# Start the scheduler
scheduler.start()


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


# get accept user with job_id
@app.route('/analyze-notify-accepted/<job_id>', methods=['GET'])
def get_and_notify_accepted_candidates(job_id):
    applications = collection.find({'job_id': job_id})
    scored_applications = [(s, s['final_score']) for s in applications]
    scored_applications.sort(key=lambda x: x[1], reverse=True)
    top_20_percent_index = len(scored_applications) * 20 // 100
    top_applications = [s[0] for s in scored_applications[:top_20_percent_index]]

    # Convert ObjectId to string
    for s in top_applications:
        s['_id'] = str(s['_id'])
        print(s['_id'])

    if top_applications:
        return jsonify(top_applications), 200
    else:
        return jsonify({"message": "No accepted candidates found."}), 400


@app.route('/jobss', methods=['POST'])
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


@app.route('/jobss/<job_id>', methods=['GET'])
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


# update to accepte
@app.route('/accept-application/<application_id>', methods=['PUT'])
def accept_application(application_id):
    # Fetch the application from the database
    application = db.job_applications.find_one({'_id': ObjectId(application_id)})

    if not application:
        return jsonify({'message': 'Application not found.'}), 404

    # Check if the application meets the acceptance criteria (e.g., score threshold)
    if application.get('score') >= 15:
        # Update the application status to 'accepted'
        result = db.job_applications.update_one({'_id': ObjectId(application_id)}, {'$set': {'status': 'accepted'}})

        if result.modified_count == 1:
            send_acceptance_email(application['email'], application['firstName'] + " " + application['lastName'])
            return jsonify({'message': 'Application accepted and email sent.'}), 200
        else:
            return jsonify({'message': 'No update made, application might have been already accepted.'}), 200
    else:
        # Optionally, update the status to 'refused' if it does not meet the criteria
        # This step is optional and should be used with caution to not override other statuses unintentionally
        return jsonify({'message': 'Application does not meet the acceptance criteria.'}), 400


def send_acceptance_email(email, name):
    subject = "Application Accepted"
    message = f"Dear {name},\n\nWe are pleased to inform you that your application has been accepted.\n\nBest regards,\nThe Team"
    with app.app_context():
        send_accept_email(email, subject, name)


def send_refusal_email(email, name):
    subject = "Application Not Accepted"
    message = f"Dear {name},\n\nWe regret to inform you that your application has not been accepted at this time.\n\nBest regards,\nThe Team"
    with app.app_context():
        send_refusal_email1(email, subject, name)


def get_job_applications1():
    # Assuming 'applications' is your MongoDB collection name
    return db.job_applications.find()


def analyze_and_notify_applicants():
    accepted_candidates = []
    for application in get_job_applications1():
        score = application.get('score')
        email = application.get('email')
        name = f"{application.get('firstName', '')} {application.get('lastName', '')}"
        application_id = application.get('_id')  # Assuming '_id' is stored in the application dictionary

        if score >= 50:
            # Add to accepted candidates list
            accepted_candidates.append({"name": name, "email": email})
        # else:
        # Send refusal email
        # send_refusal_email(email, name)
        # Update application status to 'refused'
        # db.job_applications.update_one({'_id': ObjectId(application_id)}, {'$set': {'status': 'refused'}})

    return accepted_candidates


# @app.route('/analyze-notify-accepted', methods=['GET'])
# def get_and_notify_accepted_candidates():
#     for application in get_job_applications1():
#         job_id = application.get('job_id')
#     accepted_candidates = evaluate_job_applications(job_id, 0.77)
#     if accepted_candidates:
#         return jsonify(accepted_candidates), 200
#     else:
#         return jsonify({"message": "No accepted candidates found or an error occurred."}), 404


def fetch_applications_and_job_ids():
    # Connect to your database
    db = mongo.db  # Assuming you're using MongoDB with Flask-PyMongo

    # Query the database for all applications
    applications = db.applications.find()

    # Extract job IDs and applications
    job_ids = set()
    application_list = []
    for app in applications:
        job_ids.add(app['job_id'])
        application_list.append(app)

    return list(job_ids), application_list
