class User:
    def __init__(self, email, birthdate, title, password, lastname, name, profile_picture=None, role="user"):
        self.lastname = lastname
        self.name = name
        self.email = email
        self.role = role
        self.password = password
        self.title = title
        self.profile_picture = profile_picture
        self.birthdate = birthdate
