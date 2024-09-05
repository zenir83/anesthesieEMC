from flask import Flask, render_template, jsonify
from openai import OpenAI
import random
import os
import sqlite3
import re
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
    "Critical Care", "Obstetric Anesthesia", "Neuro Anesthesia", "ATLS", "APLS", "Pharmacology", "Intensive Care Medicine"
]

# Initialize the database
def init_db():
    with sqlite3.connect('mcq.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_answer TEXT NOT NULL
            )
        ''')
        conn.commit()

# Store a new question in the database
def store_question(mcq):
    with sqlite3.connect('mcq.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO questions (question, options, correct_answer)
            VALUES (?, ?, ?)
        ''', (mcq['question'], '|'.join(mcq['options']), mcq['correct_answer']))
        conn.commit()

# Retrieve the last 5 questions from the database HIER ZIT WAARSCHIJNLIJK EEN PROBLEEM!
def get_last_five_questions():
    with sqlite3.connect('mcq.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date, question, options, correct_answer
            FROM questions
            ORDER BY id DESC
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
    prompt = f"Generate a challegening multiple-choice question on {topic} for anesthesiologists and residents with 4 options and provide the correct answer."
    try:
        # Using the latest OpenAI API format
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )

        # Extract the message content from the response
        result = completion.choices[0].message.content.strip()
        print(f"Raw API response: {result}")  # Debug: Print the raw response

        # Split the response into lines
        lines = result.split("\n")
        
        # Initialize question, options, and correct_answer
        question = ""
        options = []
        correct_answer = ""

        # Extract the question (assuming it's the first line)
        if lines:
            question = lines[0].strip()

        # Extract options from lines
        for line in lines[1:]:
            line = line.strip()
            # Match lines with options, e.g., "A) Option 1" or "1. Option 1"
            if re.match(r"^[A-D]\)", line) or re.match(r"^\d+\.", line):
                options.append(line)
            elif line.lower().startswith("correct answer:"):
                correct_answer = line.split(":", 1)[-1].strip()

        # Debug: Print extracted options and correct answer
        print(f"Extracted Options: {options}")
        print(f"Extracted Correct Answer: {correct_answer}")

        # Ensure the correct answer is not mistakenly included in options
        if correct_answer and correct_answer not in options:
            options.append(correct_answer)

        # Validate the correct number of options
        if len(options) < 4:
            raise ValueError(f"Not enough options generated: {options}")

        return {
            "question": question,
            "options": options,
            "correct_answer": correct_answer
        }

    except Exception as e:
        # Detailed error logging
        print(f"Error generating MCQ: {e}")
        return {
            "question": "Error generating question",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Option A",
            "error_message": str(e)  # Include the error message in the response for debugging
        }





@app.route('/')
def index():
    init_db()
    today = datetime.now().strftime('%Y-%m-%d')
    history = get_last_five_questions()

    # Initialize mcq with a default empty dictionary
    mcq = history.get(today, {})

    # Generate a new question if today's question is not in history
    if not mcq:
        mcq = generate_mcq()
        store_question(today, mcq)
        history = get_last_five_questions()

    # Debugging: Check the mcq object to ensure it has data
    print(f"MCQ Data: ", mcq)  # This will print only if mcq is defined correctly

    return render_template('index.html', mcq=generate_mcq(), history=history)


@app.route('/api/mcq')
def api_mcq():
    mcq = generate_mcq()
    return jsonify(mcq)

if __name__ == "__main__":
    app.run(debug=True)