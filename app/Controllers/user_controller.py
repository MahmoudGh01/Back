from app.Models.user import User


class UserController:
    @staticmethod
    def get_all_users(db):
        users = User.find_all(db)
        serialized_users = []
        for user in users:
            user['_id'] = str(user['_id'])  # Convert ObjectId to string
            serialized_users.append(user)
        return serialized_users
