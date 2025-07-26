from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client.get_database()
users = db.users

class User(UserMixin):
    def __init__(self, username, name=None, gmail=None, password=None, password_hash=None, _id=None, profile_image=None):
        self.username = username
        self.name = name
        self.gmail = gmail
        self.password_hash = password_hash if password_hash else (generate_password_hash(password) if password else None)
        self._id = _id
        self.profile_image = profile_image

    def get_id(self):
        return str(self._id)

    @staticmethod
    def get(user_id):
        user_data = users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(
                username=user_data['username'],
                name=user_data.get('name'),
                gmail=user_data.get('gmail'),
                password_hash=user_data.get('password_hash'),
                _id=user_data['_id'],
                profile_image=user_data.get('profile_image')
            )
        return None

    @staticmethod
    def get_by_username(username):
        user_data = users.find_one({'username': username})
        if user_data:
            return User(
                username=user_data['username'],
                name=user_data.get('name'),
                gmail=user_data.get('gmail'),
                password_hash=user_data.get('password_hash'),
                _id=user_data['_id'],
                profile_image=user_data.get('profile_image')
            )
        return None

    @staticmethod
    def get_by_gmail(gmail):
        user_data = users.find_one({'gmail': gmail})
        if user_data:
            return User(
                username=user_data['username'],
                name=user_data.get('name'),
                gmail=user_data.get('gmail'),
                password_hash=user_data.get('password_hash'),
                _id=user_data['_id'],
                profile_image=user_data.get('profile_image')
            )
        return None

    def save(self):
        if not self._id:
            result = users.insert_one({
                'username': self.username,
                'name': self.name,
                'gmail': self.gmail,
                'password_hash': self.password_hash,
                'profile_image': self.profile_image
            })
            self._id = result.inserted_id
        else:
            users.update_one(
                {'_id': self._id},
                {'$set': {
                    'username': self.username,
                    'name': self.name,
                    'gmail': self.gmail,
                    'password_hash': self.password_hash,
                    'profile_image': self.profile_image
                }}
            )
        return self

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) 