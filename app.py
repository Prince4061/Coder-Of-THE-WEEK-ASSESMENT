from flask import Flask, render_template, request, jsonify, send_file
import csv
import json
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

app = Flask(__name__)
DB_FILE = 'scores.csv'
QUESTIONS_FILE = 'questions.json'
RAPID_QUESTIONS_FILE = 'rapid_questions.json'

# Initialize questions.json with default template if not exists
def init_questions():
    if not os.path.exists(QUESTIONS_FILE):
        default_qs = [
            {
                "id": "1", 
                "text": "What is the capital of India?", 
                "options": {"a": "Mumbai", "b": "New Delhi", "c": "Kolkata", "d": "Chennai"}, 
                "answer": "b"
            },
            {
                "id": "2", 
                "text": "Which programming language is used for Flask?", 
                "options": {"a": "Java", "b": "Python", "c": "C++", "d": "Ruby"}, 
                "answer": "b"
            },
            {
                "id": "3", 
                "text": "Who is known as the father of computers?", 
                "options": {"a": "Charles Babbage", "b": "Alan Turing", "c": "Bill Gates", "d": "Steve Jobs"}, 
                "answer": "a"
            }
        ]
        with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_qs, f, indent=4)

def load_questions():
    init_questions()
    try:
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def init_rapid_questions():
    if not os.path.exists(RAPID_QUESTIONS_FILE):
        default_qs = [
            {
                "id": "1", 
                "text": "[RAPID] What is 2 + 2?", 
                "options": {"a": "3", "b": "4", "c": "5", "d": "6"}, 
                "answer": "b"
            }
        ]
        with open(RAPID_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_qs, f, indent=4)

def load_rapid_questions():
    init_rapid_questions()
    try:
        with open(RAPID_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

# Initialize scores DB
if not os.path.exists(DB_FILE):
    with open(DB_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Score'])

def read_db():
    users = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    row['Score'] = int(row['Score']) # ensure score is integer
                    users.append(row)
                except ValueError:
                    pass
    return users

def write_db(users):
    with open(DB_FILE, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ['ID', 'Name', 'Score']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)


# ==== FRONT PAGES ==== #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test_page():
    return render_template('test.html')

@app.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/rapid-test')
def rapid_test_page():
    return render_template('rapid_test.html')


# ==== ADMIN APIS ==== #

def sanitize_questions_data(js_data):
    if isinstance(js_data, dict):
        for key in ["questions", "data", "quiz"]:
            if key in js_data and isinstance(js_data[key], list):
                js_data = js_data[key]
                break

    if not isinstance(js_data, list):
        raise ValueError("JSON structure must be a list of questions (or wrapped in a dict with a 'questions' key).")
        
    sanitized = []
    for idx, item in enumerate(js_data):
        if not isinstance(item, dict):
            continue
        q = {}
        q['id'] = str(item.get('id', str(idx + 1)))
        q['text'] = str(item.get('text', 'Missing question text'))
        
        raw_options = item.get('options', {})
        clean_options = {}
        if isinstance(raw_options, list):
            keys = ['a', 'b', 'c', 'd', 'e', 'f']
            for i, opt in enumerate(raw_options):
                if i < len(keys):
                    clean_options[keys[i]] = str(opt)
        elif isinstance(raw_options, dict):
            for k, v in raw_options.items():
                clean_k = str(k).lower().strip('. )')
                if clean_k.startswith('option '):
                    clean_k = clean_k.replace('option ', '').strip()
                clean_options[clean_k] = str(v)
        else:
            clean_options = {"a": str(raw_options)}
            
        q['options'] = clean_options
        raw_answer = str(item.get('answer', 'a')).lower().strip('. )')
        if raw_answer.startswith('option '):
            raw_answer = raw_answer.replace('option ', '').strip()
            
        if raw_answer in clean_options:
            q['answer'] = raw_answer
        else:
            found_key = raw_answer
            for k, v in clean_options.items():
                if raw_answer == str(v).lower().strip('. )'):
                    found_key = k
                    break
            q['answer'] = found_key
            
        sanitized.append(q)
    return sanitized

@app.route('/api/upload-questions', methods=['POST'])
def upload_questions():
    if 'file' not in request.files:
        print("Upload Error: No file part in request.files")
        return jsonify({"success": False, "message": "No file part"}), 400
    
    file = request.files['file']
    print(f"Received file upload attempt: {file.filename}")
    
    if file.filename == '':
        print("Upload Error: No selected file")
        return jsonify({"success": False, "message": "No selected file"}), 400
    
    if file and file.filename.endswith('.json'):
        try:
            content = file.read().decode('utf-8-sig')
            print(f"Extracted content length: {len(content)}")
            
            raw_js_data = json.loads(content)
            js_data = sanitize_questions_data(raw_js_data)
                
            # Overwrite the existing questions.json file securely
            with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(js_data, f, indent=4)
                
            print("Upload Success!")
            return jsonify({"success": True, "message": "Questions updated successfully!"})
        except BaseException as e:
            print(f"Upload Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "message": f"Data Error in JSON file: {str(e)}"}), 400
            
    print("Upload Error: Filename does not end with .json")
    return jsonify({"success": False, "message": "Only .json files are allowed!"}), 400

@app.route('/api/download-template', methods=['GET'])
def download_template():
    init_questions() # Make sure it exists
    
    from flask import make_response
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        data = f.read()
        
    response = make_response(data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=questions_template.json'
    return response


@app.route('/api/upload-rapid-questions', methods=['POST'])
def upload_rapid_questions():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    if file and file.filename.endswith('.json'):
        try:
            content = file.read().decode('utf-8-sig')
            raw_js_data = json.loads(content)
            js_data = sanitize_questions_data(raw_js_data)
            
            with open(RAPID_QUESTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(js_data, f, indent=4)
            return jsonify({"success": True, "message": "Rapid Questions updated successfully!"})
        except BaseException as e:
            return jsonify({"success": False, "message": f"Data Error: {str(e)}"}), 400
    return jsonify({"success": False, "message": "Only .json files are allowed!"}), 400

@app.route('/api/download-rapid-template', methods=['GET'])
def download_rapid_template():
    init_rapid_questions()
    from flask import make_response
    with open(RAPID_QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        data = f.read()
    response = make_response(data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=rapid_questions_template.json'
    return response


# ==== TEST APIS ==== #

@app.route('/api/questions', methods=['GET'])
def get_questions():
    # Send questions dynamically loaded from JSON without the answers
    test_q = []
    all_qs = load_questions()
    for q in all_qs:
        test_q.append({
            "id": q.get("id"),
            "text": q.get("text"),
            "options": q.get("options", {})
        })
    return jsonify(test_q)

@app.route('/api/submit-test', methods=['POST'])
def submit_test():
    data = request.json
    name = data.get('name', 'Anonymous')
    answers = data.get('answers', {})
    
    all_qs = load_questions()
    score = 0
    analysis_data = []
    
    for q in all_qs:
        ans_key = answers.get(str(q['id']))
        correct_key = q.get('answer', '')
        
        user_answered = q.get('options', {}).get(ans_key, 'Skipped')
        correct_answer = q.get('options', {}).get(correct_key, 'Unknown')
        
        is_correct = (ans_key and ans_key.lower() == str(correct_key).lower())
        if is_correct:
            score += 1
            
        analysis_data.append(f"Q: {q['text']} | Student: {user_answered} | Correct: {correct_answer} | Is Correct: {is_correct}")
            
    users = read_db()
    new_id = str(len(users) + 1)
    users.append({
        'ID': new_id,
        'Name': name,
        'Score': score
    })
    write_db(users)
    
    ai_feedback = f"""
        <div style='margin-bottom: 0.8rem;'><strong style='color:#34d399;'>📊 Score:</strong> You scored {score} out of {len(all_qs)}!</div>
        <div><strong style='color:#fbbf24;'>💡 Suggestion:</strong> Keep practicing to improve further.</div>
    """
    
    return jsonify({"success": True, "score": score, "total": len(all_qs), "feedback": ai_feedback, "message": "Test submitted successfully!"})

@app.route('/api/rapid-questions', methods=['GET'])
def get_rapid_questions():
    test_q = []
    all_qs = load_rapid_questions()
    # Limit to 20 questions for rapid round
    for q in all_qs[:20]:
        test_q.append({
            "id": q.get("id"),
            "text": q.get("text"),
            "options": q.get("options", {})
        })
    return jsonify(test_q)

@app.route('/api/submit-rapid-test', methods=['POST'])
def submit_rapid_test():
    data = request.json
    name = data.get('name', 'Anonymous')
    answers = data.get('answers', {})
    
    all_qs = load_rapid_questions()[:20]
    score = 0
    analysis_data = []
    
    for q in all_qs:
        ans_key = answers.get(str(q['id']))
        correct_key = q.get('answer', '')
        user_answered = q.get('options', {}).get(ans_key, 'Skipped')
        correct_answer = q.get('options', {}).get(correct_key, 'Unknown')
        is_correct = (ans_key and ans_key.lower() == str(correct_key).lower())
        if is_correct:
            score += 1
        analysis_data.append(f"Q: {q['text']} | Student: {user_answered} | Correct: {correct_answer} | Is Correct: {is_correct}")
    
    # Intentionally skipping saving to DB per user request to not build a leaderboard
    
    ai_feedback = f"""
        <div style='margin-bottom: 0.8rem;'><strong style='color:#34d399;'>⚡ Rapid Round:</strong> You scored {score} out of {len(all_qs)}!</div>
        <div><strong style='color:#fbbf24;'>💡 Suggestion:</strong> Great speed! Keep practicing.</div>
    """
    
    return jsonify({"success": True, "score": score, "total": len(all_qs), "feedback": ai_feedback, "message": "Rapid Test submitted successfully!"})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    users = read_db()
    # Sort users by Score in descending order
    users.sort(key=lambda x: int(x.get('Score', 0)), reverse=True)
    return jsonify(users)

if __name__ == '__main__':
    app.run(debug=True)
