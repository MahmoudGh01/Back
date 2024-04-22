import datetime
import os
from datetime import datetime, timedelta
from math import ceil
from flask import request

import nltk
import spacy
from apscheduler.schedulers.background import BackgroundScheduler
from bson import ObjectId
from flask import jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Resource
from keybert import KeyBERT
from pdfminer.high_level import extract_text
from sentence_transformers import SentenceTransformer, util
from textblob import TextBlob

from app import app, mongo, api
from app.Controllers.JobController import JobController
from app.Controllers.auth import send_accept_email, send_refusal_email1
from app.Models import JobModel
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


@app.route('/job-applications/', methods=['GET'])
@jwt_required()
def get_job_applications():
    try:
        # Get the email from the JWT claims
        print(request.headers.get('Authorization'))  # For debugging
        identity = get_jwt_identity()
        print("User email from JWT:", identity)

        # Fetch the user object by email to get the user ID
        user = UserRepository.find_by_email(mongo, identity)
        if not user:
            print(f"No user found with the email: {identity}")
            return jsonify({"error": "User not found"}), 404

        # The user's '_id' is the 'userID' in the job_application collection
        user_id_str = str(user['_id'])
        print(f"User ID as string: {user_id_str}")

        # Query the job_application collection using the string 'userID'
        cursor = db.job_applications.find({'userID': user_id_str})
        applications = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])  # Convert ObjectId to string for JSON serialization
            applications.append(doc)

        print(f"Applications fetched for user {user_id_str}:", applications)
        return jsonify(applications)
    except Exception as e:
        print("Error fetching applications:", str(e))
        return jsonify({"error": str(e)}), 500


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


nlp = spacy.load("en_core_web_md")
nltk.download('wordnet')


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
nlp = spacy.load("en_core_web_md")
# Load a pre-trained sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')


# IA Analyze Skills User
def analyze_skills_with_ai_enhanced(user_skills, job_required_skills):
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Generate embeddings
    user_embeddings = model.encode(user_skills, convert_to_tensor=True)
    job_embeddings = model.encode(job_required_skills, convert_to_tensor=True)

    # Calculate similarities
    similarities = util.pytorch_cos_sim(user_embeddings, job_embeddings)

    # Define a threshold for considering a match (e.g., 0.4)
    match_threshold = 0.4

    # Count matches above the threshold
    matches = (similarities > match_threshold).sum()

    # Calculate percentage score
    if len(job_required_skills) > 0:
        percentage_score = ((matches / len(job_required_skills)).item()) * 100
    else:
        percentage_score = 0  # Avoid division by zero

    return percentage_score


def analyze_cover_letter_transformers(cover_letter):
    # Initialize models
    kw_model = KeyBERT(model='all-MiniLM-L6-v2')
    st_model = SentenceTransformer('all-MiniLM-L6-v2')

    # Analyze linguistic quality (grammar, sentiment)
    blob = TextBlob(cover_letter)
    grammar_quality = blob.sentences[0].polarity  # Simple sentiment as a proxy for positivity
    complexity_score = len(blob.words) / len(blob.sentences)  # Word to sentence ratio

    # Extract and evaluate key skills/keywords
    keywords = kw_model.extract_keywords(cover_letter, keyphrase_ngram_range=(1, 2), stop_words='english',
                                         use_maxsum=True, top_n=5)
    keyword_embeddings = st_model.encode([kw[0] for kw in keywords], convert_to_tensor=True)
    cover_letter_embedding = st_model.encode(cover_letter, convert_to_tensor=True)
    if keyword_embeddings.shape[0] > 0:
        if keyword_embeddings.shape[0] > 1:
            keyword_mean_embedding = keyword_embeddings.mean(dim=0)
        else:
            keyword_mean_embedding = keyword_embeddings

        coherence_score = util.pytorch_cos_sim(cover_letter_embedding, keyword_mean_embedding).item()
    else:
        coherence_score = 0  # Set a default value if no keywords are extracted

    # Combine scores into a final assessment
    final_score = ((grammar_quality + 1) / 2 * 25) + (complexity_score * 25) + (coherence_score * 50)

    # Convert to percentage
    final_score_percentage = final_score * 100

    return final_score_percentage


def find_meeting_time(job_availabilities, user_availabilities):
    """
    Finds a meeting time given job and user availabilities.

    Args:
    - job_availabilities: List of tuples representing available datetime ranges for the job [(start, end), ...]
    - user_availabilities: List of tuples representing available datetime ranges for the user [(start, end), ...]

    Returns:
    - A list of datetime objects representing the start time of possible meetings.
    """

    # Convert string datetime to actual datetime objects if they are not already
    job_availabilities = [(datetime.strptime(start, "%Y-%m-%d %H:%M"), datetime.strptime(end, "%Y-%m-%d %H:%M"))
                          for start, end in job_availabilities]
    user_availabilities = [(datetime.strptime(start, "%Y-%m-%d %H:%M"), datetime.strptime(end, "%Y-%m-%d %H:%M"))
                           for start, end in user_availabilities]

    # Meeting duration in minutes
    meeting_duration = 30

    # Find overlaps
    possible_meetings = []
    for job_start, job_end in job_availabilities:
        for user_start, user_end in user_availabilities:
            # Find the overlap range
            overlap_start = max(job_start, user_start)
            overlap_end = min(job_end, user_end)

            # Check if there is enough time for a meeting
            if (overlap_end - overlap_start) >= timedelta(minutes=meeting_duration):
                possible_meetings.append(overlap_start)

    # Return possible meeting start times
    return possible_meetings


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
        print("userId request form :" + data.get('userId'))
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
        print("new_application['job_id']: " + new_application['job_id'])
        job = job_controller.get_job_by_id(new_application['job_id'])
        job_controller.get_job_by_id(job_id)
        print("Job: " + job.get('jobTitle'))
        # Dynamically determine the required skills, here as an example
        required_skills = job.get('requirements', [])

        # Calculate individual scores
        score_cv = analyze_skills_with_spacy(extract_text_from_pdf(filename), required_skills)
        score_skills = analyze_skills_with_ai_enhanced(user_skills, required_skills)
        score_cover_letter = analyze_cover_letter_transformers(new_application['coverLetter'])

        # Calculate the final score as an average of individual scores
        final_score = (score_cv + score_skills + score_cover_letter) / 3

        # Convert filename to string before storing
        new_application['cvPdf'] = str(filename)
        new_application['score_cv'] = score_cv
        new_application['score_skills'] = score_skills
        new_application['score_cover_letter'] = score_cover_letter
        new_application['final_score'] = final_score

        # print("new _application"+new_application)
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


def scheduled_evaluation(job_id, end_date):
    # Fetch the applications for the specific job
    applications_for_job = list(db.job_applications.find({'job_id': job_id}))
    print(f"Applications for job {job_id}: {applications_for_job}")

    # Analyze and score each application
    scored_applications = []
    for app in applications_for_job:
        # Assuming 'final_score' is correctly calculated and stored in each app document
        final_score = app.get('final_score')
        user = db.users.find_one({'_id': ObjectId(app.get('userID'))})
        user_name = user.get('name')
        print(f"Final score: {final_score}")
        scored_applications.append((app, final_score))

    print(f"Scored applications: {scored_applications}")

    # Sort applications by score in descending order
    scored_applications.sort(key=lambda x: x[1], reverse=True)

    # Determine the index for the top 20% of applications
    top_20_percent_index = ceil(len(scored_applications) * 20 / 100)
    print(f"Top 20% index: {top_20_percent_index}")

    # Process the top 20% of applications
    for app, score in scored_applications[:top_20_percent_index]:
        user = db.users.find_one({'_id': ObjectId(app.get('userID'))})
        user_name = user.get('name')
        user_email = user.get('email')
        send_acceptance_email(user_email, user_name)
        db.job_applications.update_one(
            {'_id': ObjectId(app.get('_id'))},
            {'$set': {'status': 'accepted'}}
        )
        print(f"Accepted: {user_email} with final score {score}")

    # Process the bottom 80% of applications
    for app, score in scored_applications[top_20_percent_index:]:
        user = db.users.find_one({'_id': ObjectId(app.get('userID'))})
        user_name = user.get('name')
        user_email = user.get('email')
        send_refusal_email(user_email, user_name)
        db.job_applications.update_one(
            {'_id': ObjectId(app.get('_id'))},
            {'$set': {'status': 'refused'}}
        )
        print(f"Refused: {user_email} with final score {score}")


applications_cursor = db.job_applications.find()
job_controller = JobController(mongo)

# Create a set to store unique job IDs
job_ids = set()

# Iterate over the cursor to extract job IDs and add them to the set
for y in applications_cursor:
    job_ids.add(y.get('job_id'))

print(f"Unique Job ID: {job_ids}")

for job_id in job_ids:
    # Fetch the job document from the database using the job ID
    job = job_controller.get_job_by_id(job_id)
    if job:
        end_date = job.get('end_date')
        print(f"Job end_date: {end_date}")

        if end_date:
            # Convert end_date to datetime object using datetime.strptime
            end_date_datetime = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
            print(f"Job end_datess: {end_date_datetime}")

            # Schedule the evaluation function to run at the specific date and time
            scheduler.add_job(scheduled_evaluation, 'date', run_date=end_date_datetime, args=[job_id, end_date])

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
