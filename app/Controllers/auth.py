import os
import random
import string

from flask import render_template_string
from flask_jwt_extended import create_access_token
from flask_mail import Message
from werkzeug.utils import secure_filename

from app import mail, app
from app.Repository.UserRepo import UserRepository, PasswordResetCode

from app.Utils.utils import hash_password, verify_password


class AuthController:
    @staticmethod
    def set_password(db, email, new_password):
        user = UserRepository.find_by_email(db,email)
        if not user:
            return {'error': f'Email {email} not found'}, 404

        hashed_password = hash_password(new_password)
        UserRepository.update_password(db, email, hashed_password)

        return {'message': 'Password reset successful'}, 200

    @staticmethod
    def verify_code(db, email, code):
        stored_code = PasswordResetCode.find_code(db, email, code)
        if not stored_code:
            return {'error': 'Invalid verification code'}, 400
        return {'message': 'Verification code is valid'}, 200

    def reset_password(db, email, new_password):
        user = UserRepository.find_by_email(email)
        if not user:
            return {'error': 'Email not found'}, 404

        hashed_password = hash_password(new_password)
        UserRepository.update_password(db, email, hashed_password)

        return {'message': 'Password reset successful'}, 200

    @staticmethod
    def forgot_password(db, email):
        user = UserRepository.find_by_email(email)
        if not user:
            return {'error': 'Email not found'}, 404

        new_verification_code = generate_random_code()
        PasswordResetCode.insert_code(db, email, new_verification_code)

        subject = "Password Reset Verification Code"
        send_email(email, subject, new_verification_code)

        return {'message': 'Verification code sent to your email'}, 200

    @staticmethod
    def signup(db,email, name, password, file,role):
        if not (email and name and password and file):
            return {'message': 'Missing information'}, 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        existing_user = UserRepository.find_by_email(db,email)
        if existing_user:
            return {'message': 'Email already exists'}, 409

        user_id = UserRepository.create_user(db,email, password, name, profile_picture=file_path,role=role)
        return {'message': 'User created successfully', 'user_id': str(user_id)}, 201

    @staticmethod
    def signin(db,email, password):
        user = UserRepository.find_by_email(db,email)
        if user and verify_password(user['password'], password):
            access_token = create_access_token(identity=email)
            user_data = {
                "password": user['password'],
                "name": user['name'],
                "email": user['email'],
                "_id": str(user['_id'])  # Assuming MongoDB usage
            }
            return {"token": access_token, "user": user_data}, 200
        else:
            return {'error': 'Invalid credentials'}, 401


def send_email1(recipient, subject, verification_code, email):
    # Read the HTML template from the mail.html file
    with open('app/Mail.html', 'r') as file:
        html_content = file.read()

    # Render the HTML template with the verification code
    html_content = render_template_string(html_content, verification_code=verification_code, email=email)

    # Send the email
    msg = Message(subject, recipients=[recipient])
    msg.html = html_content
    mail.send(msg)


# Function to generate a random verification code
def generate_random_code(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def send_email(recipient, subject, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    mail.send(msg)
# Function to send an email with the verification code
