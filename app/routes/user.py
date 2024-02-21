from flask import redirect, jsonify
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token

from flask_restx import Resource
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pymongo.server_api import ServerApi

from app import app, api, mongo, CLIENT_ID, URL_DICT, CLIENT, DATA
from app.Controllers.auth import AuthController
from app.Controllers.user_controller import UserController
from app.Models.Payloads import signin_model, forgot_password_model, verify_code_model, set_password_model, \
    reset_password_model
from app.Models.user import User
from app.Repository.User import UserRepository

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api.route('/signup')
class Signup(Resource):
    @staticmethod
    def post():
        """Create a new user with profile picture"""
        if 'file' not in request.files:
            return {'message': 'No file part'}, 401

        file = request.files['file']
        if file.filename == '':
            return {'message': 'No selected file'}, 402

        if file and allowed_file(file.filename):
            email = request.form.get('email')
            name = request.form.get('name')
            password = request.form.get('password')
            role = request.form.get('role')

            # Delegate to AuthController
            return AuthController.signup(mongo, email, name, password, file, role)
        else:
            return {'message': 'Invalid file type'}, 400


# Assuming you have the necessary imports and api setup

@api.route('/signin')
class Signin(Resource):
    @api.expect(signin_model, validate=True)
    def post(self):
        """Sign in user"""
        json_data = request.json
        email = json_data.get('email')
        password = json_data.get('password')

        # Delegate to AuthController
        return AuthController.signin(mongo, email, password)


# Assuming necessary imports are already done

@api.route('/users')
class UserList(Resource):
    @jwt_required()
    def get(self):
        """List all users"""
        # Directly using mongo.db might require you to import or access the database instance appropriately
        serialized_users = UserController.get_all_users(mongo.db)
        return serialized_users, 200

    @api.route('/forgot_password')
    class ForgotPassword(Resource):
        @api.expect(forgot_password_model, validate=True)
        def post(self):
            """Forgot password"""
            email = request.json.get('email')
            return AuthController.forgot_password(mongo, email)

    @api.route('/reset_password')
    class ResetPassword(Resource):
        @api.expect(reset_password_model, validate=True)
        def post(self):
            """Reset password"""
            json_data = request.json
            email = json_data['email']
            new_password = json_data['new_password']

            # Delegate to AuthController
            return AuthController.reset_password(mongo, email, new_password)

        @api.route('/ping')
        class ping(Resource):
            def post(self):
                """Reset password"""

                # Send a ping to confirm a successful connection
                try:
                    res = mongo.admin.command('ping')
                    print("Pinged your deployment. You successfully connected to MongoDB!")
                except Exception as e:
                    print(e)
                    return 401

                # Delegate to AuthController
                return 200

        @api.route('/set-password')
        class SetPassword(Resource):
            @api.expect(set_password_model, validate=True)
            def post(self):
                """Reset password"""
                json_data = request.json
                email = json_data['email']
                new_password = json_data['password']

                # Delegate the business logic to the AuthController
                return AuthController.set_password(mongo, email, new_password)

        @api.route('/verify_code')
        class VerifyCode(Resource):
            @api.expect(verify_code_model, validate=True)
            def post(self):
                """Verify verification code"""
                json_data = request.json
                email = json_data['email']
                code = json_data['code']

                # Delegate business logic to the AuthController
                return AuthController.verify_code(mongo, email, code)


def exchange_token(code):
    try:
        # Exchange the authorization code for an ID token
        id_token_info = id_token.verify_oauth2_token(
            code,
            google_requests.Request(),
            CLIENT_ID
        )

        # Verify the issuer
        if id_token_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        # Return the ID token info
        return id_token_info

    except ValueError as e:
        print("Error verifying ID token:", str(e))
        return None


@api.route('/google-sign-in', methods=['GET', 'POST'])
class GoogleSignIn(Resource):
    def post(self):
        # Check if the request is JSON or form-encoded

        if request.is_json:
            code = request.get_json().get('code')
        else:
            code = request.form.get('code')

        print(code)

        # Redirect to Google Sign-In if 'code' parameter is missing
        if not code:
            google_signin_url = CLIENT.prepare_request_uri(
                URL_DICT['google_oauth'],
                redirect_uri=DATA['redirect_uri'],
                scope=DATA['scope'],
                prompt=DATA['prompt']
            )
            return redirect(google_signin_url)

        # Exchange authorization code for ID token
        id_token_info = exchange_token(code)

        if id_token_info is None:
            return "Error during token exchange", 400

        # Extract necessary information from the ID token info
        email = id_token_info.get('email')
        sub = id_token_info.get('sub')  # Google user ID
        name = id_token_info.get('name')
        picture = id_token_info.get('picture')

        # Insert user data into MongoDB
        user_data = {
            'name': name,
            'email': email,
            'picture': picture,
            'google_id': sub
        }
        UserRepository.find_by_email(mongo, email)

        token = create_access_token(identity=email)

        result = mongo.db.users.insert_one(user_data)
        user_id = result.inserted_id
        # Prepare the response to match the Flutter fromJson method
        response_body = {
            "user": {
                "_id": str(user_id),
                "name": user_data['name'],
                "email": user_data['email'],
                # Assume default values for fields not present in the user_data
                "password": "",  # It's unusual to send passwords back. Consider removing this.
                "file": picture  # If you have a profile picture path, include it here.
            },
            "token": token
        }

        return response_body, 200


@api.route('/whoami', methods=['GET'])
class WhoAmI(Resource):
    @jwt_required()
    def get(self):
        claims = get_jwt()
        # Assuming you have an 'identity' claim containing the user's email or username
        identity = get_jwt_identity()
        if identity:
            user = UserRepository.find_by_email(mongo, identity)
            if user:
                # Customize this response based on what user information you want to return
                user_info = {
                    "email": user.get("email"),
                    "name": user.get("name"),
                    "role": user.get("role")
                }
                return {"user": user_info, "claims": claims}, 200
            else:
                return {"msg": "User not found"}, 404
        else:
            return {"msg": "Invalid JWT claims"}, 400
