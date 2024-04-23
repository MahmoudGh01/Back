from bson import ObjectId
from flask import Flask, jsonify,request
import openai
import random
import time
from flask_cors import CORS
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

@app.route('/quiz', methods=['GET'])
def list_questions():
    questions = [
        {
            "question": "What is the output of this Java code?\n\npublic class Main {\n    public static void main(String[] args) {\n        int x = 5;\n        System.out.println(x++);\n    }\n}",
            "options": [
                "5",
                "6",
                "Compiler Error",
                "Runtime Error"
            ],
            "correct": 0
        },
        {
            "question": "What is the syntax to declare an array in Java?",
            "options": [
                "int[] arr;",
                "int arr[];",
                "int arr{};",
                "int arr();"
            ],
            "correct": 0
        },
        {
            "question": "Which method is automatically called when an object is created in Java?",
            "options": [
                "start()",
                "run()",
                "begin()",
                "construct()"
            ],
            "correct": 3
        },
        {
            "question": "What is the base class for all classes in Java?",
            "options": [
                "System",
                "Object",
                "Class",
                "Base"
            ],
            "correct": 1
        },
        {
            "question": "What is the output of this Java code?\n\npublic class Main {\n    public static void main(String[] args) {\n        int x = 10;\n        int y = 20;\n        System.out.println(x > y ? x : y);\n    }\n}",
            "options": [
                "10",
                "20",
                "Compiler Error",
                "Runtime Error"
            ],
            "correct": 1
        },
        {
            "question": "Which interface is implemented by all Java collection classes?",
            "options": [
                "List",
                "Set",
                "Map",
                "Collection"
            ],
            "correct": 3
        },
        {
            "question": "Which keyword is used to inherit a class in Java?",
            "options": [
                "extends",
                "implements",
                "inherit",
                "extends/implements"
            ],
            "correct": 0
        },
        {
            "question": "What is the output of this Java code?\n\npublic class Main {\n    public static void main(String[] args) {\n        String str = null;\n        System.out.println(str.length());\n    }\n}",
            "options": [
                "null",
                "0",
                "Compiler Error",
                "Runtime Error"
            ],
            "correct": 3
        },
        {
            "question": "What is the result of 10 + 20 / 5 in Java?",
            "options": [
                "8",
                "10",
                "14",
                "12"
            ],
            "correct": 2
        },
        {
            "question": "What is the output of this Java code?\n\npublic class Main {\n    public static void main(String[] args) {\n        int x = 5;\n        System.out.println(x << 2);\n    }\n}",
            "options": [
                "20",
                "10",
                "5",
                "Compiler Error"
            ],
            "correct": 0
        }
    ]

    #quiz_data = {
     #   "theme": "java",
      #  "questions": questions
    #}

    #result = mongo.db.quizs.insert_one(quiz_data)
    #inserted_id = str(result.inserted_id)
    json_data = json.loads(json.dumps(questions, default=str))

    return jsonify(json_data), 200


@app.route('/delete_quiz/<id>', methods=['DELETE'])
def delete_quiz(id):
    quiz_id = ObjectId(id)
    # Supprimer le quiz de la collection
    result = mongo.db.quizs.delete_one({'_id': quiz_id})

    if result.deleted_count == 1:
        return jsonify({'message': f'Quiz avec l\'ID {id} supprimé avec succès'}), 200
    else:
        return jsonify({'message': f'Aucun quiz trouvé avec l\'ID {id}'}), 404

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
    idRecruter = json_data.get("idRecruter")


    quiz_data = {
        "idRecruter": idRecruter,
        "theme": theme,
        "questions": questions
    }
    result = mongo.db.quizs.insert_one(quiz_data)
    inserted_id = str(result.inserted_id)

    return jsonify({"message": "Quiz inserted successfully.", "inserted_id": inserted_id}), 200
@app.route('/affecter', methods=['POST'])
def affecter_quiz_candidat():

    json_data = request.json
    idRecruter = json_data.get("idRecruter")
    idcandidat = json_data.get("idcandidat")
    idquiz = json_data.get("idquiz")
    date = json_data.get("date")
    quiz_data = {

        "idRecruter": idRecruter,
        "idCandidat": idcandidat,
        "idQuiz": idquiz,
        "date": date,
        "score": 0,
        "status": "start"
    }
    result = mongo.db.testquiz.insert_one(quiz_data)
    inserted_id = str(result.inserted_id)

    return jsonify({"message": "Quiz inserted successfully.", "inserted_id": inserted_id}), 200
@app.route('/onequiz/<quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    try:
        # Convert the quiz_id string to ObjectId
        quiz_object_id = ObjectId(quiz_id)
        quiz = mongo.db.quizs.find_one({'_id': quiz_object_id})
        if quiz:
            # Convert ObjectId to string
            quiz['_id'] = str(quiz['_id'])
            return jsonify(quiz), 200
        else:
            return jsonify({'message': 'Quiz not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/onecandidat/<candidat_id>', methods=['GET'])
def get_candidat(candidat_id):
    try:
        # Convert the quiz_id string to ObjectId
        candidat_object_id = ObjectId(candidat_id)
        candidat = mongo.db.users.find_one({'_id': candidat_object_id})
        if candidat:
            # Convert ObjectId to string
            candidat['_id'] = str(candidat['_id'])
            return jsonify(candidat), 200
        else:
            return jsonify({'message': 'candidat not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/all_candidat', methods=['GET'])
def allcandidat():
    try:
        # Query all users with role "candidat"
        candidats_cursor = mongo.db.users.find({"role": "user"})

        # Initialize an empty list to hold the processed documents
        candidats_list = []

        # Iterate through the cursor to access each document
        for candidat in candidats_cursor:
            # Convert '_id' field to string
            candidat['_id'] = str(candidat['_id'])
            # Append the processed document to the list
            candidats_list.append(candidat)

        # Return the list of candidates as JSON with a 200 status code
        return jsonify(candidats_list), 200

    except Exception as e:
        # Return an error message in JSON with a 500 status code in case of an exception
        return jsonify({'error': str(e)}), 500




@app.route('/allQuizByRecruter/<idRecruter>', methods=['GET'])
def allQuizByRecruter(idRecruter):
    result = mongo.db.quizs.find({"idRecruter":idRecruter})
    list_quiz = list(result)
    # Convert to JSON serializable format
    json_data = json.loads(json.dumps(list_quiz, default=str))

    return jsonify(json_data), 200

@app.route('/testQuizByRecruter/<idRecruter>', methods=['GET'])
def allTestQuizByRecruter(idRecruter):
    result = mongo.db.testquiz.find({"idRecruter":idRecruter})
    list_test_quiz = list(result)
    # Convert to JSON serializable format
    json_data = json.loads(json.dumps(list_test_quiz, default=str))

    return jsonify(json_data), 200


@app.route('/testQuizByCandidat/<idCandidat>', methods=['GET'])
def allTestQuizByCandidat(idCandidat):
    result = mongo.db.testquiz.find({"idCandidat":idCandidat})
    list_test_quiz = list(result)
    # Convert to JSON serializable format
    json_data = json.loads(json.dumps(list_test_quiz, default=str))

    return jsonify(json_data), 200


@app.route('/update_test_quiz/<string:test_quiz_id>', methods=['PUT'])
def update_test_quiz(test_quiz_id):
    try:
        # Récupérer les données du test quiz à partir de la requête
        data = request.json
        new_score = data.get('score')
        new_status = data.get('status')

        # Vérifier si le test quiz existe dans la base de données
        test_quiz = mongo.db.testquiz.find_one({'_id': ObjectId(test_quiz_id)})
        if not test_quiz:
            return jsonify({'error': 'Test quiz not found'}), 404

        # Mettre à jour le score et le statut du test quiz
        mongo.db.testquiz.update_one({'_id': ObjectId(test_quiz_id)}, {'$set': {'score': new_score, 'status': new_status}})

        return jsonify({'message': 'Test quiz updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500