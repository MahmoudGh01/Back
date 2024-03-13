from flask import Flask, jsonify, request
import openai
import random
import time
import json

from app import app, mongo

openai.api_key = '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'


# Fonction pour générer une question avec 4 options
def generer_question(theme):
    requete = f"Generate a question about {theme}:"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": requete}],
            temperature=0.5,
            max_tokens=100
        )
    except openai.error.RateLimitError:
        # Si une erreur de limite de taux est rencontrée, attendez 20 secondes et réessayez
        time.sleep(20)
        return generer_question(theme)

    question = response['choices'][0]['message']['content'].strip()

    options = []
    correct_option_index = random.randint(0, 3)  # Index de l'option correcte
    for i in range(4):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": f"Generate an option for the question: {question}"}],
                temperature=0.7,
                max_tokens=20
            )
        except openai.error.RateLimitError:
            # Si une erreur de limite de taux est rencontrée, attendez 20 secondes et réessayez
            time.sleep(20)
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": f"Generate an option for the question: {question}"}],
                temperature=0.7,
                max_tokens=20
            )

        option = response.choices[0]['message']['content'].strip()
        options.append(option)  # Option correcte

    return {"question": question, "options": options, "correct": correct_option_index}


@app.route('/quiz', methods=['POST'])
def list_questions():
    questions = [
        {
            "question": "What language is used to develop Flutter apps?",
            "options": [
                "Java",
                "Dart",
                "Python",
                "C#"
            ],
            "correct": 1
        },
        {
            "question": "What is the primary function of the 'pubspec.yaml' file in a Flutter project?",
            "options": [
                "To define the app's layout",
                "To declare the app's dependencies",
                "To configure the app's database",
                "To specify the app's permissions"
            ],
            "correct": 1
        },
        {
            "question": "What widget is used to create a button in Flutter?",
            "options": [
                "Text",
                "Button",
                "FlatButton",
                "WidgetButton"
            ],
            "correct": 2
        },
        {
            "question": "What command is used to run a Flutter app in debug mode?",
            "options": [
                "flutter start",
                "flutter run",
                "flutter debug",
                "flutter launch"
            ],
            "correct": 1
        },
        {
            "question": "What is the purpose of the 'setState' method in Flutter?",
            "options": [
                "To change the state of the widget",
                "To set the initial state of the widget",
                "To update the UI when the state of the widget changes",
                "To reset the state of the widget"
            ],
            "correct": 2
        },
        {
            "question": "Which of the following is a layout widget in Flutter?",
            "options": [
                "Text",
                "Container",
                "Image",
                "Row"
            ],
            "correct": 3
        },
        {
            "question": "What is the main function in a Flutter app used for?",
            "options": [
                "To define the app's theme",
                "To declare the app's routes",
                "To specify the app's dependencies",
                "To start the app's execution"
            ],
            "correct": 3
        },
        {
            "question": "Which package is used for making HTTP requests in Flutter?",
            "options": [
                "http",
                "networking",
                "http_request",
                "dart:io"
            ],
            "correct": 0
        },
        {
            "question": "What is the purpose of the 'Scaffold' widget in Flutter?",
            "options": [
                "To provide a canvas for drawing",
                "To define the structure of the app's UI",
                "To manage the app's state",
                "To handle user gestures"
            ],
            "correct": 1
        },
        {
            "question": "What is the output of this Flutter code?\n\nText('Hello, World!')",
            "options": [
                "A button",
                "A text field",
                "A text widget displaying 'Hello, World!'",
                "An error"
            ],
            "correct": 2
        }
    ]
    quiz_data = {
        "theme": "Flutter",
        "questions": questions
    }
    result = mongo.db.quizs.insert_one(quiz_data)
    inserted_id = str(result.inserted_id)
    return jsonify({"message": "Quiz inserted successfully.", "inserted_id": inserted_id}), 200


# Fonction pour générer un quiz avec 10 questions
def generer_quiz(theme):
    quiz = []
    for _ in range(5):
        question_data = generer_question(theme)
        quiz.append(question_data)
    return quiz


@app.route('/generer_quiz/<theme>', methods=['GET'])
def generer_quiz_route(theme):
    quiz = generer_quiz(theme)
    return jsonify(quiz), 200


@app.route('/add_quiz', methods=['POST'])
def addQuiz():
    json_data = request.json
    theme = json_data.get("theme")
    questions = json_data.get("questions")

    quiz_data = {
        "theme": theme,
        "questions": questions
    }
    result = mongo.db.quizs.insert_one(quiz_data)
    inserted_id = str(result.inserted_id)

    return jsonify({"message": "Quiz inserted successfully.", "inserted_id": inserted_id}), 200


@app.route('/all_quiz', methods=['GET'])
def allQuiz():
    result = mongo.db.quizs.find()
    list_quiz = list(result)
    # Convert to JSON serializable format
    json_data = json.loads(json.dumps(list_quiz, default=str))

    return jsonify(json_data), 200
