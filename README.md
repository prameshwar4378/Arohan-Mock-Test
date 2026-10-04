# Arohan Academy English School - Mock Test Portal

A complete, production-ready, mobile-first MCQ-based Mock Test software for **Arohan Academy English School**, built entirely in **Python & Django** with **Django Templates** on the frontend and Django on the backend.

---

## 🌟 Key Features

### 1. Dedicated, Custom Supervisor / Superuser Control Center (No Default Admin Dependency)
- **Custom Supervisor Login:** Secure, professional login page at `/supervisor/login/` with custom SaaS styling. Access to all administrative tools is strictly protected.
- **Custom Executive Dashboard (`/supervisor/dashboard/`):**
  - Interactive **Chart.js** data visualizations (Weekly attempts trend line chart, Pass vs. Fail ratio doughnut chart).
  - High-level KPI metric cards (Batches, Enrolled Students, Mock Tests, Questions Bank, Total Submissions).
  - Live Submissions Feed with quick links to view detailed evaluation reports.
  - Class and Mock Test summary tables.
- **Full Academic Operations Control:**
  - **Class & Batch Management (`/supervisor/classes/`):** Create, edit, and delete classes; view enrolled rosters and assigned exams.
  - **Student Management & Performance Audit (`/supervisor/students/`):** Search and filter students by class, add/edit/delete students.
  - **Individual Student Audit (`/supervisor/students/<id>/`):** See how many exams any student has attempted, all past scores, attempt numbers, and click to view the complete question-by-question verification sheet.
  - **Mock Tests Catalog (`/supervisor/exams/`):** Create, configure, publish/unpublish mock tests, set time limits, negative marking, and passing criteria.

### 2. High-Productivity Bulk Question Paper Importer (`/supervisor/bulk-questions/`)
- **Mode 1 - Smart Text / AI-Style Paste Parser:**
  - Copy and paste an entire question paper directly from Microsoft Word, PDF, or text notes!
  - Automatically parses question text, 4 options (A, B, C, D), correct answer (`Ans: B` or `Answer: B`), and step-by-step solutions/explanations.
  - **Live Interactive Preview:** Review all parsed questions in visual cards with highlighted correct answers and explanations before saving.
  - **1-Click "Load Sample Question Text"** button provided for quick reference and instant testing.
  - **1-Click "Confirm & Save All"** bulk-inserts all questions into the database instantly.
- **Mode 2 - CSV File Upload:**
  - Standard spreadsheet upload with a downloadable sample CSV template.

### 3. Public Student Flow (Zero Credential Barrier)
- Students do not need to register, remember passwords, or create accounts.
- **Step 1:** Student selects their **Class / Batch**.
- **Step 2:** Student selects their **Name** from the public class roster (with real-time search/filtering by name or roll number).
- **Step 3:** Student selects the **Mock Test** available for their class.
- **Step 4:** Review test rules and launch the **Live CBT (Computer Based Test)**.

### 4. Modern CBT Exam Runner
- Live Countdown Timer (auto-submits upon time expiration).
- Question Palette (Answered in green, Unanswered in orange, Marked for Review in purple, Not Visited in gray).
- Instant jump to any question, clear response, and review tagging.
- Submission confirmation modal showing summary before final submit.

### 5. Instant Verification & Confirmation Report
- Real-time score calculation upon submission.
- Summary Card: Score, Maximum Marks, Percentage, Pass/Fail status, Time Spent, Accuracy rate.
- **Question-by-Question Verification**:
  - Correct option highlighted in **Green** with checkmark.
  - Student's selected option highlighted in **Green** (if right) or **Red** (if wrong).
  - Step-by-step **Solution & Explanation** displayed for every question.
  - Print-optimized view for saving or printing the report as PDF.

### 6. Unlimited Exam Retakes
- No attempt limits! A student can attempt the same mock test as many times as they want to practice.
- Every attempt is tracked with an incremental attempt number (`Attempt #1`, `Attempt #2`, `Attempt #3`...).
- Multi-attempt progress comparison table displayed on the result page.

---

## 🚀 How to Run the Application

### 1. Start the Development Server
Open PowerShell in this directory and execute:
```powershell
python manage.py runserver
```

### 2. Access the Application
- **Public Student Portal:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Supervisor Login:** [http://127.0.0.1:8000/supervisor/login/](http://127.0.0.1:8000/supervisor/login/)
- **Supervisor Dashboard:** [http://127.0.0.1:8000/supervisor/dashboard/](http://127.0.0.1:8000/supervisor/dashboard/)
- **Bulk Question Paper Importer:** [http://127.0.0.1:8000/supervisor/bulk-questions/](http://127.0.0.1:8000/supervisor/bulk-questions/)
- **Students Audit & History:** [http://127.0.0.1:8000/supervisor/students/](http://127.0.0.1:8000/supervisor/students/)
- **Django Admin (Optional):** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🔑 Default Supervisor / Superuser Credentials
- **Username:** `admin`
- **Password:** `admin123`

---

## 🧪 Pre-loaded Sample Data (Seeded)
The application includes realistic sample data ready to test immediately:
1. **Classes:** Class 10 (Science & Mathematics), Class 12 (Physics & Chemistry), Foundation Batch.
2. **Students:** 12 enrolled students across all 3 classes (e.g. *Aarav Sharma [ARO-101]*, *Priya Patel [ARO-102]*, *Diya Mukherjee [ARO-201]*, etc.).
3. **Exams & Questions:** 3 complete mock tests with MCQs, scoring rules, negative marking, and detailed explanations.
4. **Sample Attempt:** Pre-loaded attempt for Aarav Sharma to demonstrate result reports immediately.

To re-seed fresh sample data anytime:
```powershell
python manage.py seed_data
```

---

## 🧪 Running Automated Tests
To run the automated test suite:
```powershell
python manage.py test
```
All 10 end-to-end unit tests verify student navigation, CBT exam runner, grading, negative marking, multiple retakes, verification reports, custom supervisor login, custom supervisor dashboard, and smart bulk question paper parsing.
