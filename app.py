import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, redirect, url_for
import joblib
import numpy as np
import mysql.connector
import bcrypt
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.metrics import r2_score   
from flask import send_file
import io
from flask import session

app = Flask(__name__)
app.secret_key = "studytrack_ai_super_secret_key"


def read_dataset(file):
    filename = file.filename.lower()

    if filename.endswith(".csv"):
        return pd.read_csv(file)

    elif filename.endswith(".xlsx"):
        return pd.read_excel(file)

    else:
        raise ValueError("Unsupported file format")


# initially setting models to none beacause still not yet trained. 
reg_model = None
kmeans_model = None


#for backend database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Rashid@mysql",
        database="studytrack_ai"
    )

#whenever the user open the link initially.flask runs and send html page to browser
@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"].encode("utf-8")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
    result = cursor.fetchone()
    conn.close()

    if result and bcrypt.checkpw(password, result[0].encode()):
        return redirect("/home")
    return "Invalid Login"


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    password = bcrypt.hashpw(
        request.form["password"].encode("utf-8"),
        bcrypt.gensalt()
    )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password) VALUES (%s,%s,%s)",
        (request.form["username"], request.form["email"], password)
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/logout")
def logout():
    return redirect("/")


#Home
@app.route("/home")
def home():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")#counts total registered users
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions")#counts total predictions
    total_predictions = cursor.fetchone()[0]

    try:
        with open("ml/model_accuracy.txt") as f:
            model_accuracy = f.read()
    except:
        model_accuracy = "N/A"

    conn.close()

    return render_template(
        "home.html",
        total_users=total_users,
        total_predictions=total_predictions,
        model_accuracy=model_accuracy
    )


#model training
@app.route("/train", methods=["GET", "POST"])
def train_model():
    global reg_model, kmeans_model

    if request.method == "GET":
        return render_template("train_model.html")
    file = request.files["dataset"]
    data = read_dataset(file)


    features = [
        "StudyHours",
        "PlayHours",
        "SleepHours",
        "SocialMedia",
        "Exercise",
        "AttentionLevel"
    ]

    X = data[features]
    y = data["Marks"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    reg_model = LinearRegression()
    reg_model.fit(X_train, y_train)

    accuracy = r2_score(y_test, reg_model.predict(X_test))

    kmeans_model = KMeans(n_clusters=3, random_state=42)
    kmeans_model.fit(X)

    os.makedirs("ml", exist_ok=True)
    joblib.dump(reg_model, "ml/regression_model.pkl")
    joblib.dump(kmeans_model, "ml/kmeans_model.pkl")

    accuracy_after = round(accuracy * 100, 2)

# Save latest accuracy
    with open("ml/model_accuracy.txt", "w") as f:
        f.write(str(accuracy_after))

# Save accuracy history (for visualization)
    history_file = "ml/accuracy_history.txt"

    if not os.path.exists(history_file):
    # baseline before training (dummy / previous model)
        with open(history_file, "w") as f:
            f.write("70\n")   # baseline accuracy

    with open(history_file, "a") as f:
        f.write(str(accuracy_after) + "\n")

    return render_template("train_model.html", accuracy=round(accuracy * 100, 2))


# single prediction
@app.route("/predict", methods=["GET", "POST"])
def predict():
    global reg_model, kmeans_model

    if reg_model is None or kmeans_model is None:
        return render_template("model_not_trained.html")


    if request.method == "GET":
        return render_template("prediction.html")

    student = request.form["student"]

    input_data = np.array([[
        float(request.form["StudyHours"]),
        float(request.form["PlayHours"]),
        float(request.form["SleepHours"]),
        float(request.form["SocialMedia"]),
        float(request.form["Exercise"]),
        float(request.form["AttentionLevel"])
    ]])

    predicted_marks = round(reg_model.predict(input_data)[0], 2)

    if predicted_marks >= 85:
        level = "High Performer"
        recommendation = "Maintain consistency and revise regularly."
    elif predicted_marks >= 65:
        level = "Average Performer"
        recommendation = "Reduce distractions and improve focus."
    else:
        level = "Needs Improvement"
        recommendation = "Increase study hours and reduce social media."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO predictions
        (student_name, study_hours, play_hours, sleep_hours,
         social_media, exercise, attention_level,
         predicted_marks, performance_level, recommendation)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            student,
            *input_data[0],
            predicted_marks,
            level,
            recommendation
        )
    )
    conn.commit()
    conn.close()

    return render_template(
        "prediction_result.html",
        student=student,
        marks=predicted_marks,
        level=level,
        recommendation=recommendation
    )


# bulk prediction
@app.route("/bulk", methods=["GET", "POST"])
def bulk_prediction():
    global reg_model

    #mod not train
    if reg_model is None:
        return render_template(
            "model_not_trained.html",
            feature="Bulk Prediction"
        )

    # get request
    if request.method == "GET":
        return render_template("bulk_predictions.html")

    #post req
    if "dataset" not in request.files:
        return render_template(
            "bulk_predictions.html",
            error="Please upload a CSV file."
        )

    file = request.files["dataset"]

    if file.filename == "":
        return render_template(
            "bulk_predictions.html",
            error="No file selected."
        )

    # read csv
    try:
        file = request.files["dataset"]
        data = read_dataset(file)

    except Exception as e:
        return render_template(
            "bulk_predictions.html",
            error="Invalid CSV file."
        )

    results = []

    conn = get_db_connection()
    cursor = conn.cursor()

    #process rows
    for _, row in data.iterrows():
        student = row["Student"]

        input_data = np.array([[
            float(row["StudyHours"]),
            float(row["PlayHours"]),
            float(row["SleepHours"]),
            float(row["SocialMedia"]),
            float(row["Exercise"]),
            float(row["AttentionLevel"])
        ]])

        predicted_marks = round(reg_model.predict(input_data)[0], 2)

        if predicted_marks >= 85:
            level = "High Performer"
            recommendation = "Maintain consistency and revise regularly."
        elif predicted_marks >= 65:
            level = "Average Performer"
            recommendation = "Reduce distractions and improve focus."
        else:
            level = "Needs Improvement"
            recommendation = "Increase study hours and reduce social media."

        cursor.execute(
            """
            INSERT INTO predictions
            (student_name, study_hours, play_hours, sleep_hours,
             social_media, exercise, attention_level,
             predicted_marks, performance_level, recommendation)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                student,
                row["StudyHours"],
                row["PlayHours"],
                row["SleepHours"],
                row["SocialMedia"],
                row["Exercise"],
                row["AttentionLevel"],
                predicted_marks,
                level,
                recommendation
            )
        )

        results.append({
            "student": student,
            "marks": predicted_marks,
            "level": level,
            "recommendation": recommendation
        })
    session["bulk_results"] = results

    conn.commit()
    conn.close()

    #  FINAL returning
    return render_template(
        "bulk_predictions.html",
        results=results,
        success=True
    )
     
@app.route("/download-bulk-results")
def download_bulk_results():
    results = session.get("bulk_results")

    if not results:
        return "No bulk prediction results available."

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Student",
        "Predicted Marks",
        "Performance Level",
        "Recommendation"
    ])

    # Rows
    for r in results:
        writer.writerow([
            r["student"],
            r["marks"],
            r["level"],
            r["recommendation"]
        ])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="bulk_prediction_results.csv"
    )

@app.route("/download-bulk-sample")
def download_bulk_sample():
    sample_csv = (
        "Student,StudyHours,PlayHours,SleepHours,SocialMedia,Exercise,AttentionLevel\n"
        "Aarav,4,2,7,3,1,7\n"
        "Ananya,6,1,8,2,1,8\n"
        "Rohan,3,3,6,4,0,6\n"
    )

    return send_file(
        io.BytesIO(sample_csv.encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="bulk_prediction_sample.csv"
    )


@app.route("/download-bulk-results-excel")
def download_bulk_results_excel():
    results = session.get("bulk_results")

    if not results:
        return "No results available"

    df = pd.DataFrame(results)

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        download_name="bulk_results.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )





# dataa visualization
@app.route("/visualize")
def visualize():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT study_hours, predicted_marks, performance_level
        FROM predictions
    """)
    data = cursor.fetchall()
    conn.close()

    if not data:
        return render_template("visualize.html", graphs=False)

    study_hours = [row[0] for row in data]
    marks = [row[1] for row in data]
    levels = [row[2] for row in data]

    os.makedirs("static/images", exist_ok=True)



    # study vs marks
    plt.figure()
    plt.scatter(study_hours, marks)
    plt.xlabel("Study Hours")
    plt.ylabel("Predicted Marks")
    plt.title("Study Hours vs Predicted Marks")
    plt.tight_layout()
    plt.savefig("static/images/study_vs_marks.png")
    plt.close()

    # Marks Distribution
    plt.figure()
    plt.hist(marks, bins=8)
    plt.xlabel("Predicted Marks")
    plt.ylabel("Count")
    plt.title("Predicted Marks Distribution")
    plt.tight_layout()
    plt.savefig("static/images/marks_distribution.png")
    plt.close()

    #  Graph 3: Performance Level 
    from collections import Counter
    level_counts = Counter(levels)

    plt.figure()
    plt.bar(level_counts.keys(), level_counts.values())
    plt.xlabel("Performance Level")
    plt.ylabel("Students")
    plt.title("Performance Level Distribution")
    plt.tight_layout()
    plt.savefig("static/images/performance_levels.png")
    plt.close()

    #  Graph 4: Accuracy Before vs After 
    acc_file = "ml/accuracy_history.txt"
    with open(acc_file) as f:
        acc_values = [float(x.strip()) for x in f.readlines()]

    plt.figure()
    plt.plot(range(len(acc_values)), acc_values, marker="o")
    plt.xticks([0, len(acc_values)-1], ["Before Training", "After Training"])
    plt.ylabel("Accuracy (%)")
    plt.title("Model Accuracy Improvement")
    plt.tight_layout()
    plt.savefig("static/images/accuracy_comparison.png")
    plt.close()

    return render_template("visualize.html", graphs=True)




if __name__ == "__main__":
    app.run(debug=True)
