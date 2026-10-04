from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg, Max, Q
from django.http import JsonResponse, HttpResponse
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta
import json
from decimal import Decimal

from .reports import (
    get_class_report_data, get_student_report_data,
    generate_class_excel, generate_student_excel,
    generate_class_pdf, generate_student_pdf
)

from .models import AcademicClass, Subject, Student, Exam, Question, ExamAttempt, AttemptAnswer
from .forms import (
    SuperuserLoginForm, AcademicClassForm, SubjectForm, StudentForm, ExamForm, QuestionForm,
    BulkQuestionTextForm, BulkQuestionUploadForm, BulkStudentUploadForm
)
from .utils import (
    parse_bulk_question_text, format_questions_to_text, import_questions_from_csv,
    import_students_from_csv, generate_sample_question_csv, generate_sample_student_csv
)


def supervisor_required(view_func):
    """Decorator ensuring only authenticated superusers/staff can access supervisor views."""
    decorated_view = user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or u.is_staff),
        login_url='portal:supervisor_login'
    )(view_func)
    return decorated_view


# ==============================================================================
# AUTHENTICATION
# ==============================================================================

def supervisor_login(request):
    """Dedicated Supervisor / Superuser Login Page with professional styling."""
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('portal:supervisor_dashboard')

    if request.method == 'POST':
        form = SuperuserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser or user.is_staff:
                login(request, user)
                messages.success(request, f"Welcome to Supervisor Control Center, {user.username}!")
                next_url = request.GET.get('next') or 'portal:supervisor_dashboard'
                return redirect(next_url)
            else:
                messages.error(request, "Access denied. Only supervisors and administrators are permitted.")
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")
    else:
        form = SuperuserLoginForm()

    return render(request, 'portal/supervisor/login.html', {'form': form})


def supervisor_logout(request):
    """Logs out supervisor."""
    logout(request)
    messages.info(request, "You have been logged out of the supervisor center.")
    return redirect('portal:supervisor_login')


# ==============================================================================
# DASHBOARD & ANALYTICS
# ==============================================================================

@supervisor_required
def supervisor_dashboard(request):
    """
    Executive Supervisor Dashboard with Chart.js analytics, KPI cards,
    recent attempts ledger, and class summaries.
    """
    total_classes = AcademicClass.objects.count()
    total_students = Student.objects.filter(is_active=True).count()
    total_exams = Exam.objects.count()
    total_questions = Question.objects.count()
    total_attempts = ExamAttempt.objects.count()

    recent_attempts = (
        ExamAttempt.objects.select_related('student', 'exam', 'student__student_class')
        .order_by('-started_at')[:10]
    )

    classes = AcademicClass.objects.annotate(
        student_count=Count('students', filter=Q(students__is_active=True)),
        exam_count=Count('exams', filter=Q(exams__is_active=True))
    ).order_by('name')

    exams = Exam.objects.annotate(
        attempt_count=Count('attempts'),
        avg_score=Avg('attempts__score_obtained'),
        highest_score=Max('attempts__score_obtained')
    ).order_by('-created_at')[:8]

    # Chart 1: Attempts in the last 7 days
    today = timezone.now().date()
    date_labels = []
    attempt_counts_7d = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        date_labels.append(day.strftime('%b %d'))
        count = ExamAttempt.objects.filter(
            started_at__date=day
        ).count()
        attempt_counts_7d.append(count)

    # Chart 2: Pass vs Fail distribution
    passed_attempts = ExamAttempt.objects.filter(is_passed=True).count()
    failed_attempts = ExamAttempt.objects.filter(is_passed=False).count()

    # Chart 3: Class-wise student distribution
    class_names = [c.name for c in classes[:6]]
    class_student_counts = [c.student_count for c in classes[:6]]

    context = {
        'total_classes': total_classes,
        'total_students': total_students,
        'total_exams': total_exams,
        'total_questions': total_questions,
        'total_attempts': total_attempts,
        'recent_attempts': recent_attempts,
        'classes': classes,
        'exams': exams,
        'chart_dates_json': json.dumps(date_labels),
        'chart_attempts_7d_json': json.dumps(attempt_counts_7d),
        'passed_attempts': passed_attempts,
        'failed_attempts': failed_attempts,
        'chart_class_names_json': json.dumps(class_names),
        'chart_class_students_json': json.dumps(class_student_counts),
    }
    return render(request, 'portal/supervisor/dashboard.html', context)


# ==============================================================================
# CLASS MANAGEMENT
# ==============================================================================

@supervisor_required
def supervisor_classes(request):
    """Lists all classes with quick create form."""
    if request.method == 'POST':
        form = AcademicClassForm(request.POST)
        if form.is_valid():
            academic_class = form.save()
            messages.success(request, f"Class '{academic_class.name}' created successfully.")
            return redirect('portal:supervisor_classes')
    else:
        form = AcademicClassForm()

    classes = AcademicClass.objects.annotate(
        student_count=Count('students', filter=Q(students__is_active=True)),
        exam_count=Count('exams', filter=Q(exams__is_active=True))
    ).order_by('name')

    return render(request, 'portal/supervisor/classes.html', {
        'classes': classes,
        'form': form
    })


@supervisor_required
def supervisor_class_detail(request, class_id):
    """View class details, subjects list, and roster of enrolled students."""
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    students = academic_class.students.annotate(
        attempt_count=Count('attempts')
    ).order_by('roll_number', 'name')
    exams = academic_class.exams.all().order_by('-created_at')
    subjects = academic_class.subjects.all().order_by('name')
    subject_form = SubjectForm(initial={'academic_class': academic_class})

    return render(request, 'portal/supervisor/class_detail.html', {
        'academic_class': academic_class,
        'students': students,
        'exams': exams,
        'subjects': subjects,
        'subject_form': subject_form,
    })


@supervisor_required
def supervisor_subject_create(request, class_id):
    """Add a subject to an academic class."""
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            subject, created = Subject.objects.get_or_create(
                academic_class=academic_class,
                name=name,
                defaults={'code': code, 'description': description, 'is_active': True}
            )
            if created:
                messages.success(request, f"Subject '{name}' added successfully to {academic_class.name}.")
            else:
                messages.info(request, f"Subject '{name}' already exists in {academic_class.name}.")
        else:
            messages.error(request, "Subject name is required.")
    return redirect('portal:supervisor_class_detail', class_id=academic_class.id)


@supervisor_required
def supervisor_subject_delete(request, subject_id):
    """Delete a subject from a class and detach it from exams in that class."""
    subject = get_object_or_404(Subject, id=subject_id)
    class_id = subject.academic_class_id
    subject_name = subject.name
    academic_class = subject.academic_class
    if request.method == 'POST':
        # Clean up any exams assigned to this class that had this deleted subject
        for exam in academic_class.exams.filter(subject__iexact=subject_name):
            if exam.classes.count() <= 1:
                exam.subject = ''
                exam.save(update_fields=['subject'])
            else:
                exam.classes.remove(academic_class)
        subject.delete()
        messages.success(request, f"Subject '{subject_name}' deleted.")
    return redirect('portal:supervisor_class_detail', class_id=class_id)


@supervisor_required
def supervisor_class_edit(request, class_id):
    """Edit academic class details."""
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    if request.method == 'POST':
        form = AcademicClassForm(request.POST, instance=academic_class)
        if form.is_valid():
            form.save()
            messages.success(request, f"Class '{academic_class.name}' updated successfully.")
            return redirect('portal:supervisor_classes')
    else:
        form = AcademicClassForm(instance=academic_class)

    return render(request, 'portal/supervisor/class_form.html', {
        'form': form,
        'academic_class': academic_class,
        'title': f"Edit Class: {academic_class.name}"
    })


@supervisor_required
def supervisor_class_delete(request, class_id):
    """Delete an academic class."""
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    if request.method == 'POST':
        name = academic_class.name
        academic_class.delete()
        messages.success(request, f"Class '{name}' and associated data deleted.")
        return redirect('portal:supervisor_classes')
    return render(request, 'portal/supervisor/confirm_delete.html', {
        'object_name': f"Class: {academic_class.name}",
        'cancel_url': 'portal:supervisor_classes'
    })


# ==============================================================================
# STUDENT MANAGEMENT & AUDIT
# ==============================================================================

@supervisor_required
def supervisor_students(request):
    """Student roster with class filter, search, and student creation modal."""
    classes = AcademicClass.objects.all().order_by('name')
    selected_class_id = request.GET.get('class_id')
    search_query = request.GET.get('q', '').strip()

    students = Student.objects.select_related('student_class').annotate(
        attempt_count=Count('attempts')
    )

    if selected_class_id:
        students = students.filter(student_class_id=selected_class_id)

    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | Q(roll_number__icontains=search_query)
        )

    students = students.order_by('student_class__name', 'roll_number', 'name')

    # Student creation form for modal
    form = StudentForm()

    return render(request, 'portal/supervisor/students.html', {
        'students': students,
        'classes': classes,
        'selected_class_id': selected_class_id,
        'search_query': search_query,
        'form': form,
    })


@supervisor_required
def supervisor_student_create(request):
    """Create a new student manually."""
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Student '{student.name}' ({student.roll_number}) added successfully.")
            return redirect('portal:supervisor_students')
    else:
        initial_class = request.GET.get('class_id')
        form = StudentForm(initial={'student_class': initial_class} if initial_class else None)

    return render(request, 'portal/supervisor/student_form.html', {
        'form': form,
        'title': "Add New Student"
    })


@supervisor_required
def supervisor_student_edit(request, student_id):
    """Edit student details."""
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"Student '{student.name}' updated successfully.")
            return redirect('portal:supervisor_students')
    else:
        form = StudentForm(instance=student)

    return render(request, 'portal/supervisor/student_form.html', {
        'form': form,
        'student': student,
        'title': f"Edit Student: {student.name}"
    })


@supervisor_required
def supervisor_student_delete(request, student_id):
    """Delete a single student."""
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        name = student.name
        student.delete()
        messages.success(request, f"Student '{name}' deleted successfully.")
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'portal:supervisor_students'
        return redirect(next_url)
    return render(request, 'portal/supervisor/confirm_delete.html', {
        'object_name': f"Student: {student.name} ({student.roll_number})",
        'cancel_url': request.GET.get('next') or 'portal:supervisor_students'
    })


@supervisor_required
def supervisor_students_bulk_delete(request):
    """Delete multiple students at once (Multi-selection bulk delete)."""
    if request.method == 'POST':
        student_ids = request.POST.getlist('selected_student_ids') or request.POST.getlist('student_ids')
        if not student_ids and request.POST.get('student_ids_csv'):
            student_ids = [s.strip() for s in request.POST.get('student_ids_csv').split(',') if s.strip()]

        if not student_ids:
            messages.warning(request, "No students were selected for deletion.")
            next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'portal:supervisor_students'
            return redirect(next_url)

        students_to_delete = Student.objects.filter(id__in=student_ids)
        deleted_count = students_to_delete.count()
        students_to_delete.delete()

        messages.success(request, f"Successfully deleted {deleted_count} student{'s' if deleted_count != 1 else ''}.")
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or 'portal:supervisor_students'
        return redirect(next_url)

    return redirect('portal:supervisor_students')


@supervisor_required
def supervisor_student_detail(request, student_id):
    """
    Supervisor Student Audit view:
    Shows all exams attempted by this student, attempt numbers, scores,
    and direct access to full question-by-question verification reports.
    """
    student = get_object_or_404(Student.objects.select_related('student_class'), id=student_id)
    attempts = student.attempts.select_related('exam').order_by('-started_at')

    total_attempts = attempts.count()
    exams_attempted_distinct = attempts.values('exam').distinct().count()
    avg_percentage = attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
    passed_count = attempts.filter(is_passed=True).count()

    return render(request, 'portal/supervisor/student_audit.html', {
        'student': student,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'exams_attempted_distinct': exams_attempted_distinct,
        'avg_percentage': round(avg_percentage, 1),
        'passed_count': passed_count,
    })


# ==============================================================================
# EXAM / MOCK TEST MANAGEMENT
# ==============================================================================

@supervisor_required
def supervisor_exams(request):
    """Lists all mock tests with quick stats, class and subject filters."""
    classes = AcademicClass.objects.all().order_by('name')
    selected_class_id = request.GET.get('class_id')
    selected_subject = request.GET.get('subject', '').strip()
    search_query = request.GET.get('q', '').strip()

    exams = Exam.objects.annotate(
        question_count=Count('questions'),
        attempt_count=Count('attempts'),
        avg_score=Avg('attempts__score_obtained')
    ).prefetch_related('classes').order_by('-created_at')

    if selected_class_id:
        exams = exams.filter(classes__id=selected_class_id)
    if selected_subject:
        exams = exams.filter(subject__iexact=selected_subject)
    if search_query:
        exams = exams.filter(
            Q(title__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(subject__icontains=search_query)
        )

    available_subjects = Exam.objects.exclude(subject='').values_list('subject', flat=True).distinct().order_by('subject')

    return render(request, 'portal/supervisor/exams.html', {
        'exams': exams,
        'classes': classes,
        'available_subjects': available_subjects,
        'selected_class_id': selected_class_id,
        'selected_subject': selected_subject,
        'search_query': search_query,
    })


def get_class_subjects_map():
    """
    Returns a dictionary mapping class ID (str) to class name and all active subjects.
    Prioritizes subjects from the Subject table for each class; only falls back to
    exams if no subjects are configured for that class.
    """
    classes_with_subjects = AcademicClass.objects.all().prefetch_related('subjects', 'exams').order_by('name')
    class_subjects_map = {}
    for c in classes_with_subjects:
        subs = list(c.subjects.filter(is_active=True).values_list('name', flat=True))
        if subs:
            combined = sorted(list({s.strip() for s in subs if s.strip()}), key=lambda x: x.lower())
        else:
            exam_subs = list(c.exams.filter(is_active=True).exclude(subject='').values_list('subject', flat=True).distinct())
            combined = sorted(list({s.strip() for s in exam_subs if s.strip()}), key=lambda x: x.lower())

        class_subjects_map[str(c.id)] = {
            'class_name': c.name,
            'subjects': combined
        }
    return class_subjects_map


@supervisor_required
def supervisor_api_class_subjects(request):
    """
    AJAX endpoint returning subjects available in the database for specified class IDs.
    """
    raw_ids = request.GET.getlist('class_ids')
    if not raw_ids:
        raw_param = request.GET.get('class_ids', '')
        raw_ids = [x.strip() for x in raw_param.split(',') if x.strip()]
    
    class_ids = [int(cid) for cid in raw_ids if str(cid).isdigit()]
    
    full_map = get_class_subjects_map()
    if class_ids:
        filtered_map = {str(cid): full_map.get(str(cid), {'class_name': '', 'subjects': []}) for cid in class_ids if str(cid) in full_map}
    else:
        filtered_map = full_map
        
    return JsonResponse({'success': True, 'class_subjects': filtered_map})


@supervisor_required
def supervisor_api_exam_questions(request, exam_id):
    """
    AJAX endpoint returning existing questions of an exam formatted for the Smart Parser text area.
    """
    exam = get_object_or_404(Exam, id=exam_id)
    questions = exam.questions.all().order_by('order', 'id')
    count = questions.count()
    formatted_text = format_questions_to_text(questions) if count > 0 else ""
    first_q = questions.first()

    return JsonResponse({
        'success': True,
        'exam_id': exam.id,
        'exam_title': exam.title,
        'subject': exam.subject,
        'question_count': count,
        'raw_text': formatted_text,
        'default_marks': str(first_q.marks) if first_q else "1.00",
        'default_negative_marks': str(first_q.negative_marks) if first_q else str(exam.negative_marking),
    })


@supervisor_required
def supervisor_exam_create(request):
    """Create a new mock test exam, subject-wise."""
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            # Ensure subject is saved for assigned classes that have no subjects configured yet
            if exam.subject:
                sub_clean = exam.subject.strip()
                for c in exam.classes.all():
                    if not c.subjects.filter(is_active=True).exists():
                        Subject.objects.get_or_create(academic_class=c, name=sub_clean)
            messages.success(request, f"Exam '{exam.title}' scheduled successfully! Now add questions to it.")
            return redirect('portal:supervisor_exam_detail', exam_id=exam.id)
    else:
        initial_data = {}
        class_id = request.GET.get('class_id')
        subject_name = request.GET.get('subject')
        if class_id:
            try:
                c = AcademicClass.objects.get(id=class_id)
                initial_data['classes'] = [c]
            except AcademicClass.DoesNotExist:
                pass
        if subject_name:
            initial_data['subject'] = subject_name
        form = ExamForm(initial=initial_data)

    class_subjects_map = get_class_subjects_map()
    all_subjects = Subject.objects.filter(is_active=True).values_list('name', flat=True).distinct().order_by('name')

    return render(request, 'portal/supervisor/exam_form.html', {
        'form': form,
        'title': "Schedule New Mock Test",
        'all_subjects': all_subjects,
        'class_subjects_json': json.dumps(class_subjects_map),
    })


@supervisor_required
def supervisor_exam_edit(request, exam_id):
    """Edit mock test settings and subject."""
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            exam = form.save()
            if exam.subject:
                sub_clean = exam.subject.strip()
                for c in exam.classes.all():
                    if not c.subjects.filter(is_active=True).exists():
                        Subject.objects.get_or_create(academic_class=c, name=sub_clean)
            messages.success(request, f"Exam '{exam.title}' updated successfully.")
            return redirect('portal:supervisor_exam_detail', exam_id=exam.id)
    else:
        form = ExamForm(instance=exam)

    class_subjects_map = get_class_subjects_map()
    all_subjects = Subject.objects.filter(is_active=True).values_list('name', flat=True).distinct().order_by('name')

    return render(request, 'portal/supervisor/exam_form.html', {
        'form': form,
        'exam': exam,
        'title': f"Edit Exam: {exam.title}",
        'all_subjects': all_subjects,
        'class_subjects_json': json.dumps(class_subjects_map),
    })


@supervisor_required
def supervisor_exam_delete(request, exam_id):
    """Delete a mock test."""
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        title = exam.title
        exam.delete()
        messages.success(request, f"Exam '{title}' deleted.")
        return redirect('portal:supervisor_exams')
    return render(request, 'portal/supervisor/confirm_delete.html', {
        'object_name': f"Mock Test: {exam.title}",
        'cancel_url': 'portal:supervisor_exams'
    })


@supervisor_required
def supervisor_exam_detail(request, exam_id):
    """
    Detailed exam view:
    Question bank viewer, leaderboard of student attempts, and stats.
    """
    exam = get_object_or_404(Exam.objects.prefetch_related('classes', 'questions'), id=exam_id)
    attempts = exam.attempts.select_related('student', 'student__student_class').order_by('-score_obtained', 'time_taken_seconds')
    questions = exam.questions.all().order_by('order', 'id')

    total_attempts = attempts.count()
    avg_score = attempts.aggregate(Avg('score_obtained'))['score_obtained__avg'] or 0
    highest_score = attempts.aggregate(Max('score_obtained'))['score_obtained__max'] or 0

    return render(request, 'portal/supervisor/exam_detail.html', {
        'exam': exam,
        'attempts': attempts,
        'questions': questions,
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 2),
        'highest_score': highest_score,
    })


# ==============================================================================
# SINGLE QUESTION MANAGEMENT
# ==============================================================================

@supervisor_required
def supervisor_question_create(request, exam_id):
    """Add a single question manually to an exam."""
    exam = get_object_or_404(Exam, id=exam_id)
    current_max_order = Question.objects.filter(exam=exam).count() + 1

    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            question = form.save()
            messages.success(request, f"Question Q{question.order} added successfully.")
            return redirect('portal:supervisor_exam_detail', exam_id=exam.id)
    else:
        form = QuestionForm(initial={'exam': exam, 'order': current_max_order, 'marks': Decimal('1.00')})

    return render(request, 'portal/supervisor/question_form.html', {
        'form': form,
        'exam': exam,
        'title': f"Add Question to '{exam.title}'"
    })


@supervisor_required
def supervisor_question_edit(request, question_id):
    """Edit an existing question."""
    question = get_object_or_404(Question, id=question_id)
    exam = question.exam
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, f"Question Q{question.order} updated successfully.")
            return redirect('portal:supervisor_exam_detail', exam_id=exam.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'portal/supervisor/question_form.html', {
        'form': form,
        'exam': exam,
        'question': question,
        'title': f"Edit Question Q{question.order}"
    })


@supervisor_required
def supervisor_question_delete(request, question_id):
    """Delete a question."""
    question = get_object_or_404(Question, id=question_id)
    exam_id = question.exam_id
    if request.method == 'POST':
        question.delete()
        messages.success(request, "Question deleted successfully.")
        return redirect('portal:supervisor_exam_detail', exam_id=exam_id)
    return render(request, 'portal/supervisor/confirm_delete.html', {
        'object_name': f"Question: Q{question.order} ({question.question_text[:50]}...)",
        'cancel_url': 'portal:supervisor_exam_detail',
        'cancel_id': exam_id
    })


# ==============================================================================
# BULK QUESTION PAPER IMPORTER (SMART TEXT PARSER & CSV IMPORTER)
# ==============================================================================

@supervisor_required
def supervisor_bulk_questions(request, exam_id=None):
    """
    High-productivity Bulk Question Paper Input:
    Supports:
    1. Smart Text Paste Parser: Paste 10-50 questions from Word/PDF/Notepad -> Instant Preview & Save.
       Supports loading, viewing, and updating existing questions in-place.
    2. CSV Upload: Upload CSV question bank with 1-click template.
    """
    if not exam_id:
        param_id = request.GET.get('exam_id')
        if param_id and str(param_id).isdigit():
            exam_id = int(param_id)

    initial_exam = None
    initial_text = ""
    if exam_id:
        initial_exam = get_object_or_404(Exam, id=exam_id)
        existing_qs = initial_exam.questions.all().order_by('order', 'id')
        if existing_qs.exists():
            initial_text = format_questions_to_text(existing_qs)

    text_initial_data = {}
    if initial_exam:
        text_initial_data['exam'] = initial_exam
        if initial_text:
            text_initial_data['raw_text'] = initial_text

    text_form = BulkQuestionTextForm(initial=text_initial_data if text_initial_data else None)
    csv_form = BulkQuestionUploadForm(initial={'exam': initial_exam} if initial_exam else None)

    preview_questions = None
    preview_errors = []
    selected_exam = initial_exam

    if request.method == 'POST':
        action_type = request.POST.get('action_type')

        # -------------------------------------------------------------
        # Action 1: Text Paste Preview
        # -------------------------------------------------------------
        if action_type == 'preview_text':
            text_form = BulkQuestionTextForm(request.POST)
            if text_form.is_valid():
                selected_exam = text_form.cleaned_data['exam']
                raw_text = text_form.cleaned_data['raw_text']
                def_marks = text_form.cleaned_data['default_marks']
                def_neg = text_form.cleaned_data['default_negative_marks']

                parsed, errors = parse_bulk_question_text(raw_text, def_marks, def_neg)
                preview_questions = parsed
                preview_errors = errors
                if parsed:
                    messages.info(request, f"Successfully parsed {len(parsed)} questions. Review below and choose whether to Update/Replace or Append.")
                else:
                    messages.error(request, "Could not parse any questions from the provided text. Please check the formatting.")

        # -------------------------------------------------------------
        # Action 2: Text Paste Confirm & Save (Update / Replace or Append)
        # -------------------------------------------------------------
        elif action_type == 'save_text_questions':
            exam_pk = request.POST.get('target_exam_id')
            selected_exam = get_object_or_404(Exam, id=exam_pk)
            questions_json = request.POST.get('questions_json')
            save_mode = request.POST.get('save_mode', 'append')

            if questions_json:
                try:
                    q_data_list = json.loads(questions_json)
                    num_new = len(q_data_list)

                    if save_mode == 'replace':
                        existing_questions = list(selected_exam.questions.all().order_by('order', 'id'))
                        num_existing = len(existing_questions)

                        # Update existing questions in-place
                        for i in range(min(num_existing, num_new)):
                            eq = existing_questions[i]
                            item = q_data_list[i]
                            eq.order = i + 1
                            eq.question_text = item['question_text']
                            eq.option_a = item['option_a']
                            eq.option_b = item['option_b']
                            eq.option_c = item['option_c']
                            eq.option_d = item['option_d']
                            eq.correct_option = item['correct_option']
                            eq.marks = Decimal(str(item.get('marks', 1.0)))
                            eq.negative_marks = Decimal(str(item.get('negative_marks', 0.0)))
                            eq.explanation = item.get('explanation', '')
                            eq.save()

                        # Append newly added questions
                        if num_new > num_existing:
                            new_objs = []
                            for i in range(num_existing, num_new):
                                item = q_data_list[i]
                                new_objs.append(
                                    Question(
                                        exam=selected_exam,
                                        order=i + 1,
                                        question_text=item['question_text'],
                                        option_a=item['option_a'],
                                        option_b=item['option_b'],
                                        option_c=item['option_c'],
                                        option_d=item['option_d'],
                                        correct_option=item['correct_option'],
                                        marks=Decimal(str(item.get('marks', 1.0))),
                                        negative_marks=Decimal(str(item.get('negative_marks', 0.0))),
                                        explanation=item.get('explanation', ''),
                                    )
                                )
                            Question.objects.bulk_create(new_objs)

                        # Delete excess questions if supervisor removed questions
                        elif num_new < num_existing:
                            excess_ids = [q.id for q in existing_questions[num_new:]]
                            Question.objects.filter(id__in=excess_ids).delete()

                        messages.success(request, f"🎉 Successfully updated and saved all {num_new} questions for '{selected_exam.title}'!")
                        return redirect('portal:supervisor_exam_detail', exam_id=selected_exam.id)

                    else:
                        # Append mode
                        current_order = Question.objects.filter(exam=selected_exam).count()
                        created_objs = []
                        for item in q_data_list:
                            current_order += 1
                            created_objs.append(
                                Question(
                                    exam=selected_exam,
                                    order=current_order,
                                    question_text=item['question_text'],
                                    option_a=item['option_a'],
                                    option_b=item['option_b'],
                                    option_c=item['option_c'],
                                    option_d=item['option_d'],
                                    correct_option=item['correct_option'],
                                    marks=Decimal(str(item.get('marks', 1.0))),
                                    negative_marks=Decimal(str(item.get('negative_marks', 0.0))),
                                    explanation=item.get('explanation', ''),
                                )
                            )
                        Question.objects.bulk_create(created_objs)
                        messages.success(request, f"🎉 Successfully appended {len(created_objs)} questions to '{selected_exam.title}'!")
                        return redirect('portal:supervisor_exam_detail', exam_id=selected_exam.id)

                except Exception as e:
                    messages.error(request, f"Error saving questions: {str(e)}")

        # -------------------------------------------------------------
        # Action 3: CSV File Upload
        # -------------------------------------------------------------
        elif action_type == 'upload_csv':
            csv_form = BulkQuestionUploadForm(request.POST, request.FILES)
            if csv_form.is_valid():
                selected_exam = csv_form.cleaned_data['exam']
                csv_file = csv_form.cleaned_data['csv_file']
                created, errors = import_questions_from_csv(csv_file, selected_exam)

                if created:
                    messages.success(request, f"🎉 Successfully imported {created} questions to '{selected_exam.title}' from CSV!")
                    return redirect('portal:supervisor_exam_detail', exam_id=selected_exam.id)
                if errors:
                    for err in errors[:5]:
                        messages.error(request, err)

    existing_count = selected_exam.questions.count() if selected_exam else (initial_exam.questions.count() if initial_exam else 0)

    return render(request, 'portal/supervisor/bulk_questions.html', {
        'text_form': text_form,
        'csv_form': csv_form,
        'initial_exam': initial_exam,
        'selected_exam': selected_exam,
        'existing_count': existing_count,
        'preview_questions': preview_questions,
        'preview_errors': preview_errors,
        'preview_questions_json': json.dumps([
            {
                'order': q['order'],
                'question_text': q['question_text'],
                'option_a': q['option_a'],
                'option_b': q['option_b'],
                'option_c': q['option_c'],
                'option_d': q['option_d'],
                'correct_option': q['correct_option'],
                'marks': str(q['marks']),
                'negative_marks': str(q['negative_marks']),
                'explanation': q['explanation'],
            } for q in preview_questions
        ]) if preview_questions else '[]'
    })


# ==============================================================================
# GLOBAL ATTEMPTS LEDGER
# ==============================================================================

@supervisor_required
def supervisor_attempts(request):
    """
    Redirect legacy attempts route to Students Roster & Audits,
    where comprehensive attempt ledgers and individual audit sheets are maintained.
    """
    return redirect('portal:supervisor_students')


# ==============================================================================
# PERFORMANCE & AUDIT REPORTS (Hub, Web View, PDF & Excel Exports)
# ==============================================================================

@supervisor_required
def supervisor_reports_hub(request):
    """
    Central hub for downloading and inspecting Class-wise and Student-wise reports.
    Provides direct links to interactive web reports, PDF downloads, and Excel spreadsheets.
    """
    classes = AcademicClass.objects.annotate(
        students_count=Count('students', distinct=True),
        exams_count=Count('exams', distinct=True)
    ).order_by('name')

    students = Student.objects.select_related('student_class').annotate(
        attempts_count=Count('attempts')
    ).order_by('student_class__name', 'roll_number', 'name')

    selected_class_id = request.GET.get('class_id')
    if selected_class_id:
        students = students.filter(student_class_id=selected_class_id)

    search_query = request.GET.get('q', '').strip()
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(roll_number__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    total_classes = classes.count()
    total_students = Student.objects.count()
    total_exams = Exam.objects.count()
    total_attempts = ExamAttempt.objects.count()

    return render(request, 'portal/supervisor/reports_hub.html', {
        'classes': classes,
        'students': students[:150],
        'total_classes': total_classes,
        'total_students': total_students,
        'total_exams': total_exams,
        'total_attempts': total_attempts,
        'selected_class_id': selected_class_id,
        'search_query': search_query,
    })


@supervisor_required
def supervisor_class_report(request, class_id):
    """Interactive, responsive web view for Class Report (with Print-to-PDF support)."""
    academic_class = get_object_or_404(AcademicClass, id=class_id)
    report_data = get_class_report_data(class_id)
    return render(request, 'portal/supervisor/report_class_view.html', {
        'data': report_data,
        'academic_class': academic_class,
    })


@supervisor_required
def supervisor_class_report_pdf(request, class_id):
    """Generates and downloads styled A4 PDF class performance report."""
    get_object_or_404(AcademicClass, id=class_id)
    report_data = get_class_report_data(class_id)
    pdf_bytes = generate_class_pdf(report_data)
    safe_name = slugify(report_data['class_name']) or f"class_{class_id}"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Class_Report_{safe_name}.pdf"'
    return response


@supervisor_required
def supervisor_class_report_excel(request, class_id):
    """Generates and downloads multi-sheet styled Excel (.xlsx) workbook for class."""
    get_object_or_404(AcademicClass, id=class_id)
    report_data = get_class_report_data(class_id)
    excel_bytes = generate_class_excel(report_data)
    safe_name = slugify(report_data['class_name']) or f"class_{class_id}"
    response = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Class_Report_{safe_name}.xlsx"'
    return response


@supervisor_required
def supervisor_student_report(request, student_id):
    """Interactive, responsive web view for Student Report (with Print-to-PDF support)."""
    student = get_object_or_404(Student, id=student_id)
    report_data = get_student_report_data(student_id)
    return render(request, 'portal/supervisor/report_student_view.html', {
        'data': report_data,
        'student': student,
    })


@supervisor_required
def supervisor_student_report_pdf(request, student_id):
    """Generates and downloads styled A4 PDF student performance report."""
    student = get_object_or_404(Student, id=student_id)
    report_data = get_student_report_data(student_id)
    pdf_bytes = generate_student_pdf(report_data)
    safe_name = slugify(f"{report_data['roll_number']}_{report_data['name']}") or f"student_{student_id}"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Student_Report_{safe_name}.pdf"'
    return response


@supervisor_required
def supervisor_student_report_excel(request, student_id):
    """Generates and downloads multi-sheet styled Excel (.xlsx) workbook for student."""
    student = get_object_or_404(Student, id=student_id)
    report_data = get_student_report_data(student_id)
    excel_bytes = generate_student_excel(report_data)
    safe_name = slugify(f"{report_data['roll_number']}_{report_data['name']}") or f"student_{student_id}"
    response = HttpResponse(
        excel_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="Student_Report_{safe_name}.xlsx"'
    return response

