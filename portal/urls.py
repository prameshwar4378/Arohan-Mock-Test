from django.urls import path
from . import views
from . import views_supervisor

app_name = 'portal'

urlpatterns = [
    # =========================================================================
    # PUBLIC STUDENT MOCK TEST PORTAL (No login required)
    # =========================================================================
    path('', views.index, name='index'),
    path('api/class-data/<int:class_id>/', views.get_class_data, name='get_class_data'),
    path('api/student-exam-status/<int:student_id>/', views.get_student_exam_status, name='get_student_exam_status'),
    path('exam/<int:exam_id>/instruction/', views.exam_instruction, name='exam_instruction'),
    path('exam/<int:exam_id>/take/', views.exam_take, name='exam_take'),
    path('exam/<int:exam_id>/submit/', views.exam_submit, name='exam_submit'),
    path('attempt/<int:attempt_id>/result/', views.exam_result, name='exam_result'),
    path('attempt/<int:attempt_id>/pdf/', views.attempt_result_pdf, name='attempt_result_pdf'),
    path('student/<int:student_id>/history/', views.student_history, name='student_history'),

    # =========================================================================
    # SUPERVISOR / SUPERUSER CUSTOM CONTROL CENTER
    # =========================================================================
    # Authentication
    path('supervisor/login/', views_supervisor.supervisor_login, name='supervisor_login'),
    path('supervisor/logout/', views_supervisor.supervisor_logout, name='supervisor_logout'),
    path('admin-login/', views_supervisor.supervisor_login, name='admin_login_redirect'),
    path('admin-logout/', views_supervisor.supervisor_logout, name='admin_logout_redirect'),

    # Dashboard
    path('supervisor/dashboard/', views_supervisor.supervisor_dashboard, name='supervisor_dashboard'),
    path('superuser-portal/', views_supervisor.supervisor_dashboard, name='superuser_dashboard'),

    # Class Management
    path('supervisor/classes/', views_supervisor.supervisor_classes, name='supervisor_classes'),
    path('supervisor/classes/<int:class_id>/', views_supervisor.supervisor_class_detail, name='supervisor_class_detail'),
    path('supervisor/classes/<int:class_id>/edit/', views_supervisor.supervisor_class_edit, name='supervisor_class_edit'),
    path('supervisor/classes/<int:class_id>/delete/', views_supervisor.supervisor_class_delete, name='supervisor_class_delete'),
    path('supervisor/classes/<int:class_id>/subject/add/', views_supervisor.supervisor_subject_create, name='supervisor_subject_create'),
    path('supervisor/subjects/<int:subject_id>/delete/', views_supervisor.supervisor_subject_delete, name='supervisor_subject_delete'),

    # Student Management & Audit
    path('supervisor/students/', views_supervisor.supervisor_students, name='supervisor_students'),
    path('superuser-portal/students/', views_supervisor.supervisor_students, name='superuser_students'),
    path('supervisor/students/create/', views_supervisor.supervisor_student_create, name='supervisor_student_create'),
    path('supervisor/students/bulk-delete/', views_supervisor.supervisor_students_bulk_delete, name='supervisor_students_bulk_delete'),
    path('supervisor/students/<int:student_id>/', views_supervisor.supervisor_student_detail, name='supervisor_student_detail'),
    path('superuser-portal/students/<int:student_id>/', views_supervisor.supervisor_student_detail, name='superuser_student_detail'),
    path('supervisor/students/<int:student_id>/edit/', views_supervisor.supervisor_student_edit, name='supervisor_student_edit'),
    path('supervisor/students/<int:student_id>/delete/', views_supervisor.supervisor_student_delete, name='supervisor_student_delete'),

    # Exam / Mock Test Management
    path('supervisor/exams/', views_supervisor.supervisor_exams, name='supervisor_exams'),
    path('supervisor/exams/create/', views_supervisor.supervisor_exam_create, name='supervisor_exam_create'),
    path('supervisor/api/class-subjects/', views_supervisor.supervisor_api_class_subjects, name='supervisor_api_class_subjects'),
    path('supervisor/exams/<int:exam_id>/', views_supervisor.supervisor_exam_detail, name='supervisor_exam_detail'),
    path('superuser-portal/exams/<int:exam_id>/', views_supervisor.supervisor_exam_detail, name='superuser_exam_detail'),
    path('supervisor/exams/<int:exam_id>/edit/', views_supervisor.supervisor_exam_edit, name='supervisor_exam_edit'),
    path('supervisor/exams/<int:exam_id>/delete/', views_supervisor.supervisor_exam_delete, name='supervisor_exam_delete'),

    # Individual Question Management
    path('supervisor/exams/<int:exam_id>/question/add/', views_supervisor.supervisor_question_create, name='supervisor_question_create'),
    path('supervisor/questions/<int:question_id>/edit/', views_supervisor.supervisor_question_edit, name='supervisor_question_edit'),
    path('supervisor/questions/<int:question_id>/delete/', views_supervisor.supervisor_question_delete, name='supervisor_question_delete'),

    # BULK QUESTION PAPER IMPORTER (Smart Text Paste + CSV)
    path('supervisor/bulk-questions/', views_supervisor.supervisor_bulk_questions, name='supervisor_bulk_questions'),
    path('supervisor/exams/<int:exam_id>/bulk-questions/', views_supervisor.supervisor_bulk_questions, name='supervisor_exam_bulk_questions'),
    path('supervisor/api/exam-questions/<int:exam_id>/', views_supervisor.supervisor_api_exam_questions, name='supervisor_api_exam_questions'),

    # Bulk Student Upload
    path('supervisor/bulk-upload-students/', views.superuser_bulk_upload_students, name='superuser_bulk_upload_students'),
    path('supervisor/sample-students-csv/', views.download_sample_student_csv_view, name='download_sample_student_csv'),
    path('supervisor/sample-questions-csv/', views.download_sample_question_csv_view, name='download_sample_question_csv'),

    # Global Attempts Ledger
    path('supervisor/attempts/', views_supervisor.supervisor_attempts, name='supervisor_attempts'),

    # Performance Reports (Hub, Web View, PDF & Excel Exports)
    path('supervisor/reports/', views_supervisor.supervisor_reports_hub, name='supervisor_reports_hub'),
    path('supervisor/reports/class/<int:class_id>/', views_supervisor.supervisor_class_report, name='supervisor_class_report'),
    path('supervisor/reports/class/<int:class_id>/pdf/', views_supervisor.supervisor_class_report_pdf, name='supervisor_class_report_pdf'),
    path('supervisor/reports/class/<int:class_id>/excel/', views_supervisor.supervisor_class_report_excel, name='supervisor_class_report_excel'),
    path('supervisor/reports/student/<int:student_id>/', views_supervisor.supervisor_student_report, name='supervisor_student_report'),
    path('supervisor/reports/student/<int:student_id>/pdf/', views_supervisor.supervisor_student_report_pdf, name='supervisor_student_report_pdf'),
    path('supervisor/reports/student/<int:student_id>/excel/', views_supervisor.supervisor_student_report_excel, name='supervisor_student_report_excel'),
]
