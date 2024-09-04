from flask import Flask, render_template, jsonify
from openai import OpenAI
import random
import os
import sqlite3
from datetime import datetime

# Set the OpenAI API key
client = OpenAI(
    api_key = os.getenv("OPEN_AI_KEY")
)
app = Flask(__name__)

# A list of topics relevant to anesthesiology
topics = [
    "Airway Management", "Pharmacology", "Pain Management",
    "Cardiovascular Physiology", "Neuroanesthesia", "Pediatric Anesthesia",
    "Critical Care", "Obstetric Anesthesia"
]

# Initialize the database
def init_db():
    with sqlite3.connect('mcq.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_answer TEXT NOT NULL
            )
        ''')
        conn.commit()

# Store a new question in the database
def store_question(date, mcq):
    with sqlite3.connect('mcq.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO questions (date, question, options, correct_answer)
            VALUES (?, ?, ?, ?)
        ''', (date, mcq['question'], '|'.join(mcq['options']), mcq['correct_answer']))
        conn.commit()

# Retrieve the last 5 questions from the database
def get_last_five_questions():
    with sqlite3.connect('mcq.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, question, options, correct_answer
            FROM questions
            ORDER BY date DESC
            LIMIT 5
        ''')
        rows = cursor.fetchall()

        history = {}
        for row in rows:
            history[row[0]] = {
                'question': row[1],
                'options': row[2].split('|'),
                'correct_answer': row[3]
            }
        return history

def generate_mcq():
    # Select a random topic
    topic = random.choice(topics)

    # Generate the question using the OpenAI API
    prompt = f"Generate a multiple-choice question on {topic} for anesthesiologists with 4 options and provide the correct answer."
    try:
        # Using the latest OpenAI API format
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )

        # Extract the message content from the response
        result = completion.choices[0].message['content'].strip()
        print(f"Raw API response: {result}")  # Debug: Print the raw response

        # Attempt to parse the response
        lines = result.split("\n")
        question = lines[0].strip() if lines else "Question not found"

        # Filter out options, ensuring only valid lines are considered
        options = [line.strip() for line in lines[1:] if line.strip() and ':' in line]
        
        # Validate options count
        if len(options) < 4:
            raise ValueError(f"Not enough options generated: {options}")

        # Separate correct answer assumption
        correct_answer = options[-1]  # Assuming the last option is correct

        # Further checks to ensure options parsing is accurate
        if not question or len(options) < 4:
            raise ValueError("Generated content does not meet MCQ format expectations")

        return {
            "question": question,
            "options": options[:-1],  # All except last assumed to be incorrect
            "correct_answer": correct_answer
        }

    except Exception as e:
        # Detailed error logging
        print(f"Error generating MCQ: {e}")
        return {
            "question": "Error generating question",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A"
        }



@app.route('/')
def index():
    init_db()
    today = datetime.now().strftime('%Y-%m-%d')
    history = get_last_five_questions()
    
    print(f"Today's date: {today}")  # Debugging date
    print(f"History data: {history}")  # Debugging history data

    if today not in history:
        mcq = generate_mcq()
        store_question(today, mcq)
        history = get_last_five_questions()
        print(f"Generated MCQ: {mcq}")  # Debugging generated MCQ
    
    return render_template('index.html', mcq=history.get(today, {}), history=history)



@app.route('/api/mcq')
def api_mcq():
    mcq = generate_mcq()
    return jsonify(mcq)

if __name__ == "__main__":
    app.run(debug=True)