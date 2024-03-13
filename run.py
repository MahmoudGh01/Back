import base64
import os

from bson import ObjectId
from flask_cors import CORS

from app import app, mongo
from flask import Flask, request, jsonify, Response
from flask_pymongo import PyMongo, MongoClient

from app.Controllers.JobController import JobController



CORS(app)
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=10000)
