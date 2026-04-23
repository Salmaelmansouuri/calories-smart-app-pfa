from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import joblib
import numpy as np
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "super_secret_key_change_this"
CORS(app)

model = joblib.load("calories_model.pkl")
DATABASE = "database.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gender TEXT NOT NULL,
            age REAL NOT NULL,
            height REAL NOT NULL,
            weight REAL NOT NULL,
            duration REAL NOT NULL,
            heart_rate REAL NOT NULL,
            body_temp REAL NOT NULL,
            predicted_calories REAL NOT NULL,
            food_suggestion TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()


def suggest_food(calories):
    if calories < 80:
        return {
            "meal": "Fresh fruit bowl with low-fat yogurt",
            "description": "A light and refreshing option suitable after a low-energy activity. It helps maintain balance without adding excessive calories."
        }
    elif calories < 150:
        return {
            "meal": "Whole wheat toast with avocado and a glass of fresh juice",
            "description": "A moderate and balanced recovery snack that provides healthy fats, fiber, and vitamins."
        }
    elif calories < 220:
        return {
            "meal": "Turkey sandwich with salad and natural yogurt",
            "description": "A practical and nutritious meal that supports light recovery and provides a balanced mix of protein and carbohydrates."
        }
    elif calories < 300:
        return {
            "meal": "Omelette with vegetables and brown bread",
            "description": "A healthy meal rich in protein and essential nutrients, suitable after a moderate physical effort."
        }
    elif calories < 380:
        return {
            "meal": "Grilled chicken with rice and steamed vegetables",
            "description": "A well-balanced recovery meal that helps replenish energy and support muscle recovery."
        }
    elif calories < 500:
        return {
            "meal": "Salmon with sweet potato and green vegetables",
            "description": "A nutritious post-workout meal rich in protein, complex carbohydrates, and healthy fats."
        }
    else:
        return {
            "meal": "Protein-rich meal with rice, vegetables, soup, and a banana smoothie",
            "description": "A complete recovery meal recommended after high calorie expenditure to restore energy and support physical recovery."
        }


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        existing_user = cursor.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Email already exists.", "error")
            return redirect(url_for("register"))

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        conn.commit()
        conn.close()

        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    total_predictions = conn.execute("""
        SELECT COUNT(*) AS total
        FROM predictions
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()["total"]

    avg_calories_row = conn.execute("""
        SELECT AVG(predicted_calories) AS avg_calories
        FROM predictions
        WHERE user_id = ?
    """, (session["user_id"],)).fetchone()

    avg_calories = avg_calories_row["avg_calories"]
    avg_calories = round(avg_calories, 2) if avg_calories is not None else 0

    last_prediction = conn.execute("""
        SELECT predicted_calories, food_suggestion, created_at
        FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        username=session["username"],
        total_predictions=total_predictions,
        avg_calories=avg_calories,
        last_prediction=last_prediction
    )


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if "user_id" not in session:
        return redirect(url_for("login"))

    prediction = None
    food_suggestion = None

    if request.method == "POST":
        try:
            gender = request.form["gender"].strip().lower()
            age = float(request.form["age"])
            height = float(request.form["height"])
            weight = float(request.form["weight"])
            duration = float(request.form["duration"])
            heart_rate = float(request.form["heart_rate"])
            body_temp = float(request.form["body_temp"])

            if gender == "female":
                gender_encoded = 0
            elif gender == "male":
                gender_encoded = 1
            else:
                flash("Gender must be male or female.", "error")
                return redirect(url_for("predict"))

            features = np.array([[
                gender_encoded,
                age,
                height,
                weight,
                duration,
                heart_rate,
                body_temp
            ]])

            prediction = round(float(model.predict(features)[0]), 2)

            food_data = suggest_food(prediction)
            food_suggestion = f"{food_data['meal']} - {food_data['description']}"

            conn = get_db_connection()
            conn.execute("""
                INSERT INTO predictions (
                    user_id, gender, age, height, weight, duration,
                    heart_rate, body_temp, predicted_calories,
                    food_suggestion, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session["user_id"],
                gender,
                age,
                height,
                weight,
                duration,
                heart_rate,
                body_temp,
                prediction,
                food_suggestion,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            conn.close()

        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for("predict"))

    return render_template(
        "predict.html",
        prediction=prediction,
        food_suggestion=food_suggestion
    )


@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    predictions = conn.execute("""
        SELECT * FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()

    chart_labels = [item["created_at"] for item in predictions][::-1]
    chart_values = [float(item["predicted_calories"]) for item in predictions][::-1]

    return render_template(
        "history.html",
        predictions=predictions,
        chart_labels=json.dumps(chart_labels),
        chart_values=json.dumps(chart_values)
    )

@app.route("/delete_prediction/<int:prediction_id>", methods=["POST"])
def delete_prediction(prediction_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute("""
        DELETE FROM predictions
        WHERE id = ? AND user_id = ?
    """, (prediction_id, session["user_id"]))
    conn.commit()
    conn.close()

    flash("Prediction deleted successfully.", "success")
    return redirect(url_for("history"))


if __name__ == "__main__":
    init_db()
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=True)