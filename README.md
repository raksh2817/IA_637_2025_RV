# IA_637_2025_RV

# Professor-Student Project Collaboration Application

A web-based platform that connects **professors** seeking student assistance on projects with **students** looking for hands-on experience. This application allows professors to post projects, and students can apply based on their interests and skill sets.

## Table of Contents
1. [Project Topic](#project-topic)
2. [Outline of Application Purpose (Use Cases)](#outline-of-application-purpose-use-cases)
3. [ER Diagram](#ER-DIAGRAM)
4. [Relational Diagram](#Relational-Diagram)


---

## Project Topic
The **Professor-Student Project Collaboration** platform is designed to streamline collaboration between **faculty** who have research or practical projects and **students** seeking learning opportunities. This repository contains the source code and documentation for the application.

---

## Outline of Application Purpose (Use Cases)

### 1. User Registration & Authentication
- **Students** and **Professors** create accounts.
- **Login** system secured by hashed passwords.
- **Role-based dashboards** for each user type.
- **Students** can register themseleves filling out a form for login

### 2. Posting & Managing Projects (Professors)
- Professors can **create** and **update** project postings.
- Specify **required skills** and the number of students needed.
- View and manage student applications.

### 3. Searching & Applying for Projects (Students)
- Students **browse** available projects.
- Filter projects by **required skills** or department.
- **Apply** to projects that match their interests and skill sets.

### 4. Skill Management
- Students can **list** or **update** their skill profiles.
- Professors **assign** or **list** skill requirements for each project.
- **Many-to-many** relationship handled via **junction tables** (e.g., `student_skills`, `project_skills`).


### ER DIAGRAM 
![image (13)](https://github.com/user-attachments/assets/08da27bf-1522-491b-bbab-42941bfd233d)


### Relational Diagram 
![image (14)](https://github.com/user-attachments/assets/e6847824-fd9e-4779-849e-a165a1143e18)

