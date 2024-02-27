from app.Models.userModel import User
from app.Repository import UserRepo


class UserController:
    @staticmethod
    def edit_user(db, user_id, **kwargs):
        # Find the user by ID
        user = db.users.find_one({"_id": user_id})
        if not user:
            return "User not found", 404

        # Update fields if they are provided in kwargs
        if 'email' in kwargs:
            user.email = kwargs['email']
        if 'birthdate' in kwargs:
            user.birthdate = kwargs['birthdate']
        if 'title' in kwargs:
            user.title = kwargs['title']
        if 'password' in kwargs:
            user.password = kwargs['password']  # Consider hashing the password before saving
        if 'lastname' in kwargs:
            user.lastname = kwargs['lastname']
        if 'name' in kwargs:
            user.name = kwargs['name']
        if 'profile_picture' in kwargs:
            user.profile_picture = kwargs['profile_picture']
        if 'role' in kwargs:
            user.role = kwargs['role']

        # Save the updated user back to the database
        db.save(user)  # Assuming your database has a save method for updates
        return "User updated successfully", 200
    @staticmethod
    def get_all_users(db):
        users = UserRepo.UserRepository.find_all(db)
        serialized_users = []
        for user in users:
            user['_id'] = str(user['_id'])  # Convert ObjectId to string
            serialized_users.append(user)
        return serialized_users
