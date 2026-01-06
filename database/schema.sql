-- CREATE DATABASE
CREATE DATABASE IF NOT EXISTS studytrack_ai;
USE studytrack_ai;

-- USERS TABLE (LOGIN / REGISTER)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PREDICTIONS TABLE
CREATE TABLE predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    study_hours FLOAT,
    sleep_hours FLOAT,
    attendance FLOAT,
    screen_time FLOAT,
    predicted_score FLOAT,
    cluster_label INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
