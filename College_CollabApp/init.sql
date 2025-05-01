-- init.sql
-- Database creation (optional)
CREATE DATABASE IF NOT EXISTS project_portal;
USE project_portal;

-- Drop existing tables to start fresh
DROP TABLE IF EXISTS RV_Application;
DROP TABLE IF EXISTS RV_Skill;
DROP TABLE IF EXISTS RV_Project;
DROP TABLE IF EXISTS RV_User;

-- ------------------------------------------------------------------
-- 1. Users table
-- ------------------------------------------------------------------
CREATE TABLE RV_User (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin','professor','student') NOT NULL,
    date_of_creation DATE NOT NULL,
    status ENUM('pending','active','rejected') NOT NULL DEFAULT 'pending'
);

-- ------------------------------------------------------------------
-- 2. Projects table
-- ------------------------------------------------------------------
CREATE TABLE RV_Project (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    people_required INT,
    date_posted DATE NOT NULL,
    deadline DATE,
    posted_by INT NOT NULL,
    CONSTRAINT fk_project_user
      FOREIGN KEY (posted_by)
      REFERENCES RV_User(user_id)
      ON DELETE CASCADE
);

-- ------------------------------------------------------------------
-- 3. Skills table
-- ------------------------------------------------------------------
CREATE TABLE RV_Skill (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) NOT NULL,
    project_id INT  NULL,
    user_id INT     NULL,
    CONSTRAINT fk_skill_project
      FOREIGN KEY (project_id)
      REFERENCES RV_Project(project_id)
      ON DELETE CASCADE,
    CONSTRAINT fk_skill_user
      FOREIGN KEY (user_id)
      REFERENCES RV_User(user_id)
      ON DELETE CASCADE
);

-- ------------------------------------------------------------------
-- 4. Applications table
-- ------------------------------------------------------------------
CREATE TABLE RV_Application (
    app_id INT AUTO_INCREMENT PRIMARY KEY,
    app_date DATE NOT NULL,
    status ENUM('pending','accepted','rejected') NOT NULL DEFAULT 'pending',
    project_id INT NOT NULL,
    applicant_id INT NOT NULL,
    CONSTRAINT fk_app_project
      FOREIGN KEY (project_id)
      REFERENCES RV_Project(project_id)
      ON DELETE CASCADE,
    CONSTRAINT fk_applicant_user
      FOREIGN KEY (applicant_id)
      REFERENCES RV_User(user_id)
      ON DELETE CASCADE
);
