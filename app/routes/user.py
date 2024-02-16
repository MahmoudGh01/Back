from flask import redirect
from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Resource, fields
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from app import app, api, mongo, CLIENT_ID, URL_DICT, CLIENT, DATA
from app.Controllers.auth import AuthController
from app.Controllers.user_controller import UserController
from app.Models.Payloads import signin_model, forgot_password_model, verify_code_model, set_password_model, \
    reset_password_model


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


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

            # Delegate to AuthController
            return AuthController.signup(email, name, password, file)
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
        return AuthController.signin(email, password)


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
            return AuthController.forgot_password(mongo.db, email)

    @api.route('/reset_password')
    class ResetPassword(Resource):
        @api.expect(reset_password_model, validate=True)
        def post(self):
            """Reset password"""
            json_data = request.json
            email = json_data['email']
            new_password = json_data['new_password']

            # Delegate to AuthController
            return AuthController.reset_password(mongo.db, email, new_password)

        @api.route('/set-password')
        class SetPassword(Resource):
            @api.expect(set_password_model, validate=True)
            def post(self):
                """Reset password"""
                json_data = request.json
                email = json_data['email']
                new_password = json_data['password']

                # Delegate the business logic to the AuthController
                return AuthController.set_password(mongo.db, email, new_password)

        @api.route('/verify_code')
        class VerifyCode(Resource):
            @api.expect(verify_code_model, validate=True)
            def post(self):
                """Verify verification code"""
                json_data = request.json
                email = json_data['email']
                code = json_data['code']

                # Delegate business logic to the AuthController
                return AuthController.verify_code(mongo.db, email, code)


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


@app.route('/google-sign-in', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Process the POST request data here
        pass

    if request.is_json:
        code = request.get_json().get('code')
    else:
        code = request.form.get('code')

    print(code)

    if not code:
        # Redirect to the Google Sign-In link if the 'code' parameter is missing
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
        return "Error during token exchange"

    print(id_token_info)

    # Extract necessary information from the ID token info
    email = id_token_info.get('email')
    sub = id_token_info.get('sub')  # Google user ID
    name = id_token_info.get('name')
    picture = id_token_info.get('picture')
    password = "password"
    # You can now store or retrieve user data from MongoDB as needed
    # For example, you may want to save the user information to your database
    user_data = {
        'name': id_token_info.get('name', ''),
        'email': email,
        'google_id': sub
    }
    mongo.db.users.insert_one(user_data)

    return {'user_id': user_data}
