from app import mongo
from app.Utils.utils import hash_password


class User:
    def __init__(self, email, password, name, profile_picture=None):
        self.email = email

        self.password = password  # This should be hashed before storing
        self.name = name
        self.profile_picture = profile_picture  # Path or identifier for the profile picture

    @staticmethod
    def create_user(email, password, name, profile_picture=None, google_id=None):
        """
        Creates a new user document in the MongoDB database.
        """
        hashed_password = hash_password(password)  # Ensure this securely hashes the password
        user_data = {
            "email": email,
            "password": hashed_password,
            "name": name,
            "profile_picture": profile_picture,
            "google_id": google_id
        }
        result = mongo.db.users.insert_one(user_data)
        user_data['_id'] = str(result.inserted_id)  # Convert ObjectId to string
        return user_data

    @staticmethod
    def update_password(db, email, hashed_password):
        db.users.update_one({'email': email}, {'$set': {'password': hashed_password}})

    def update_user_password(user_id, hashed_password):
        """
        Met à jour le mot de passe de l'utilisateur dans la base de données.

        :param user_id: L'identifiant unique de l'utilisateur.
        :param hashed_password: Le nouveau mot de passe hashé.
        """
        try:
            # Mise à jour du document utilisateur avec le nouveau mot de passe
            result = mongo.db.users.update_one({'_id': user_id}, {'$set': {'password': hashed_password}})
            return result.modified_count > 0  # Retourne True si la mise à jour a réussi
        except Exception as e:
            print(f"Erreur lors de la mise à jour du mot de passe: {e}")
            return False

    @staticmethod
    def find_all(db):
        """
        Retrieves all user documents from the MongoDB database.
        """
        users = db.users.find()
        return list(users)

    @staticmethod
    def find_by_username(username):
        """
        Retrieves a user document from the MongoDB database by username.
        """
        user = mongo.db.users.find_one({'username': username})
        return user

    @staticmethod
    def find_by_email(email):
        """
        Retrieves a user document from the MongoDB database by email.
        """
        user = mongo.db.users.find_one({'email': email})
        return user


class PasswordResetCode:
    @staticmethod
    def insert_code(db, email, code):
        db.password_reset_codes.insert_one({'email': email, 'code': code})

    @staticmethod
    def find_code(db, email, code):
        return db.password_reset_codes.find_one({'email': email, 'code': code})
