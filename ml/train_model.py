import pandas as pd
import joblib
 # from sklearn.model_selection import train_test_split
# from sklearn.linear_model import LinearRegression
# from sklearn.cluster import KMeans
# from sklearn.metrics import r2_score

# LOAD DATA
data = pd.read_csv("../data/student_habits.csv")

X = data[["study_hours", "sleep_hours", "attendance", "screen_time"]]
y = data["score"]

# ---------------- REGRESSION ----------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

reg_model = LinearRegression()
reg_model.fit(X_train, y_train)

y_pred = reg_model.predict(X_test)
accuracy = reg_model.score(X_test, y_test)


print("Regression Accuracy:", accuracy)

# SAVE REGRESSION MODEL
joblib.dump(reg_model, "regression_model.pkl")

# ---------------- KMEANS ----------------
kmeans = KMeans(n_clusters=3, random_state=42)
kmeans.fit(X)

# SAVE KMEANS MODEL
joblib.dump(kmeans, "kmeans_model.pkl")
