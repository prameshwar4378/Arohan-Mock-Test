from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Avg, Max, Q
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal

from .models import AcademicClass, Subject, Student, Exam, Question, ExamAttempt, AttemptAnswer
from .forms import (
    SuperuserLoginForm, BulkStudentUploadForm, BulkQuestionUploadForm,
    StudentForm, AcademicClassForm, ExamForm, QuestionForm
)
from .utils import (
    generate_sample_student_csv, generate_sample_question_csv,
    import_students_from_csv, import_questions_from_csv
)
from .reports import generate_attempt_result_pdf


def is_superuser_or_staff(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


# ==============================================================================
# PUBLIC STUDENT MOCK TEST VIEWS (No student login required)
# ==============================================================================

def index(request):
    """
    Landing portal for Arohan Academy English School - Mock Test Portal.
    Allows student to select their Class, select their Name from the public class roster,
    and see all exams available for their class.
    """
    classes = AcademicClass.objects.filter(is_active=True).prefetch_related('students', 'exams')
    
    selected_class_id = request.GET.get('class_id')
    selected_class = None
    students = []
    exams = []

    if selected_class_id:
        try:
            selected_class = AcademicClass.objects.get(id=selected_class_id, is_active=True)
            students = selected_class.students.filter(is_active=True).order_by('roll_number', 'name')
            exams = selected_class.exams.filter(is_active=True).order_by('-created_at')
        except AcademicClass.DoesNotExist:
            selected_class = None

    context = {
        'classes': classes,
        'selected_class': selected_class,
        'students': students,
        'exams': exams,
        'selected_student_id': request.GET.get('student_id', ''),
        'selected_subject': request.GET.get('subject', ''),
        'selected_exam_id': request.GET.get('exam_id', ''),
        'filter_query': request.GET.get('q', ''),
    }
    return render(request, 'portal/index.html', context)


def get_class_data(request, class_id):
    """
    AJAX endpoint returning active students, available subjects, and mock tests for a selected class.
    Optionally accepts ?student_id= to include personalized attempt status.
    """
    try:
        academic_class = AcademicClass.objects.get(id=class_id, is_active=True)
        student_id = request.GET.get('student_id')
        
        status_map = {}
        if student_id:
            try:
                student = academic_class.students.get(id=student_id, is_active=True)
                attempts = ExamAttempt.objects.filter(
                    student=student,
                    is_completed=True
                ).values('exam_id').annotate(
                    count=Count('id'),
                    best_score=Max('score_obtained'),
                    best_percentage=Max('percentage'),
                    latest_id=Max('id')
                )
                for att in attempts:
                    status_map[str(att['exam_id'])] = {
                        'attempted': True,
                        'count': att['count'],
                        'best_score': float(att['best_score']),
                        'best_percentage': float(att['best_percentage']),
                        'latest_id': att['latest_id'],
                    }
            except Student.DoesNotExist:
                pass

        students_data = [
            {'id': s.id, 'name': s.name, 'roll_number': s.roll_number}
            for s in academic_class.students.filter(is_active=True).order_by('roll_number', 'name')
        ]
        exams_data = [
            {
                'id': e.id,
                'title': e.title,
                'subject': e.subject or 'General',
                'duration_minutes': e.duration_minutes,
                'total_questions': e.total_questions_count,
                'total_marks': float(e.total_marks),
                'passing_percentage': float(e.passing_percentage),
                'is_attempted': status_map.get(str(e.id), {}).get('attempted', False),
                'attempt_count': status_map.get(str(e.id), {}).get('count', 0),
                'best_score': status_map.get(str(e.id), {}).get('best_score'),
                'best_percentage': status_map.get(str(e.id), {}).get('best_percentage'),
                'latest_attempt_id': status_map.get(str(e.id), {}).get('latest_id'),
            }
            for e in academic_class.exams.filter(is_active=True).order_by('-created_at')
        ]

        # Gather active subjects for this class:
        # If the class has explicitly configured subjects in the database,
        # strictly respect those subjects (never resurrect deleted subjects).
        defined_subjects = list(
            academic_class.subjects.filter(is_active=True).values_list('name', flat=True)
        )
        seen_subjects = set()
        subjects_list = []
        has_empty_subject = False

        if defined_subjects:
            for s in defined_subjects:
                s_clean = s.strip()
                if s_clean and s_clean.lower() not in seen_subjects:
                    seen_subjects.add(s_clean.lower())
                    subjects_list.append(s_clean)
        else:
            # Fallback only for unconfigured/legacy classes with no defined subjects
            exam_subjects = list(
                academic_class.exams.filter(is_active=True)
                .exclude(subject='')
                .values_list('subject', flat=True)
                .distinct()
            )
            for s in exam_subjects:
                s_clean = s.strip()
                if s_clean and s_clean.lower() not in seen_subjects:
                    seen_subjects.add(s_clean.lower())
                    subjects_list.append(s_clean)

            has_empty_subject = academic_class.exams.filter(is_active=True, subject='').exists()
            if has_empty_subject and 'general' not in seen_subjects:
                subjects_list.append('General')

        subjects_list.sort()

        subjects_data = []
        for sub_name in subjects_list:
            if sub_name == 'General' and has_empty_subject:
                sub_exams = academic_class.exams.filter(is_active=True).filter(Q(subject__iexact='General') | Q(subject=''))
            else:
                sub_exams = academic_class.exams.filter(is_active=True, subject__iexact=sub_name)

            total_sub_exams = sub_exams.count()
            attempted_sub_count = 0
            for e in sub_exams:
                if status_map.get(str(e.id), {}).get('attempted', False):
                    attempted_sub_count += 1
            pending_sub_count = max(0, total_sub_exams - attempted_sub_count)

            subjects_data.append({
                'name': sub_name,
                'total_exams': total_sub_exams,
                'attempted_exams': attempted_sub_count,
                'pending_exams': pending_sub_count,
            })

        return JsonResponse({
            'success': True,
            'class_name': academic_class.name,
            'students': students_data,
            'subjects': subjects_data,
            'exams': exams_data,
            'status_map': status_map,
        })
    except AcademicClass.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'}, status=404)


def get_student_exam_status(request, student_id):
    """
    AJAX endpoint returning attempt status map and subject stats for a specific student across all their exams.
    Used when a student is clicked in the roster to categorize exams and subjects into Pending and Attempted.
    """
    try:
        student = Student.objects.get(id=student_id, is_active=True)
        academic_class = student.student_class

        attempts = ExamAttempt.objects.filter(
            student=student,
            is_completed=True
        ).values('exam_id').annotate(
            count=Count('id'),
            best_score=Max('score_obtained'),
            best_percentage=Max('percentage'),
            latest_id=Max('id')
        )
        status_map = {}
        for att in attempts:
            status_map[str(att['exam_id'])] = {
                'attempted': True,
                'count': att['count'],
                'best_score': float(att['best_score']),
                'best_percentage': float(att['best_percentage']),
                'latest_id': att['latest_id'],
            }

        # Calculate subject-wise breakdown for this student:
        # If the class has explicitly configured subjects, strictly respect those.
        defined_subjects = list(
            academic_class.subjects.filter(is_active=True).values_list('name', flat=True)
        )
        seen_subjects = set()
        subjects_list = []
        has_empty_subject = False

        if defined_subjects:
            for s in defined_subjects:
                s_clean = s.strip()
                if s_clean and s_clean.lower() not in seen_subjects:
                    seen_subjects.add(s_clean.lower())
                    subjects_list.append(s_clean)
        else:
            # Fallback only for unconfigured/legacy classes with no defined subjects
            exam_subjects = list(
                academic_class.exams.filter(is_active=True)
                .exclude(subject='')
                .values_list('subject', flat=True)
                .distinct()
            )
            for s in exam_subjects:
                s_clean = s.strip()
                if s_clean and s_clean.lower() not in seen_subjects:
                    seen_subjects.add(s_clean.lower())
                    subjects_list.append(s_clean)

            has_empty_subject = academic_class.exams.filter(is_active=True, subject='').exists()
            if has_empty_subject and 'general' not in seen_subjects:
                subjects_list.append('General')

        subjects_list.sort()

        subjects_data = []
        for sub_name in subjects_list:
            if sub_name == 'General' and has_empty_subject:
                sub_exams = academic_class.exams.filter(is_active=True).filter(Q(subject__iexact='General') | Q(subject=''))
            else:
                sub_exams = academic_class.exams.filter(is_active=True, subject__iexact=sub_name)

            total_sub_exams = sub_exams.count()
            attempted_sub_count = 0
            for e in sub_exams:
                if status_map.get(str(e.id), {}).get('attempted', False):
                    attempted_sub_count += 1
            pending_sub_count = max(0, total_sub_exams - attempted_sub_count)

            subjects_data.append({
                'name': sub_name,
                'total_exams': total_sub_exams,
                'attempted_exams': attempted_sub_count,
                'pending_exams': pending_sub_count,
            })

        return JsonResponse({
            'success': True,
            'student_id': student.id,
            'student_name': student.name,
            'subjects': subjects_data,
            'status_map': status_map,
        })
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)


def exam_instruction(request, exam_id):
    """
    Instructions and confirmation screen before starting the mock test.
    Validates selected student and exam eligibility.
    """
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    student_id = request.GET.get('student_id') or request.POST.get('student_id')

    if not student_id:
        messages.warning(request, "Please select your name from the student list first.")
        return redirect('portal:index')

    student = get_object_or_404(Student, id=student_id, is_active=True)

    # Verify student's class is allowed for this exam
    if not exam.classes.filter(id=student.student_class_id).exists():
        messages.error(request, f"This exam is not assigned to your class ({student.student_class.name}).")
        return redirect('portal:index')

    past_attempts = ExamAttempt.objects.filter(student=student, exam=exam).order_by('-started_at')
    attempt_count = past_attempts.count()

    context = {
        'exam': exam,
        'student': student,
        'past_attempts': past_attempts,
        'next_attempt_number': attempt_count + 1,
    }
    return render(request, 'portal/exam_instruction.html', context)


def exam_take(request, exam_id):
    """
    Live MCQ Test Runner interface.
    Features timer countdown, question palette, option selection, and submit confirmation.
    """
    exam = get_object_or_404(Exam, id=exam_id, is_active=True)
    student_id = request.GET.get('student_id') or request.POST.get('student_id')

    if not student_id:
        messages.error(request, "Please select your name to start the exam.")
        return redirect('portal:index')

    student = get_object_or_404(Student, id=student_id, is_active=True)

    if not exam.classes.filter(id=student.student_class_id).exists():
        messages.error(request, "Unauthorized access to exam.")
        return redirect('portal:index')

    questions_qs = exam.questions.all()
    if exam.shuffle_questions:
        questions = list(questions_qs.order_by('?'))
    else:
        questions = list(questions_qs.order_by('order', 'id'))

    if not questions:
        messages.warning(request, "This exam has no questions available yet. Please contact the administrator.")
        return redirect('portal:index')

    # Determine attempt number
    next_attempt_number = ExamAttempt.objects.filter(student=student, exam=exam).count() + 1

    context = {
        'exam': exam,
        'student': student,
        'questions': questions,
        'total_questions': len(questions),
        'attempt_number': next_attempt_number,
    }
    return render(request, 'portal/exam_take.html', context)


def exam_submit(request, exam_id):
    """
    Processes test submission:
    - Calculates score, correct/wrong/skipped counts.
    - Applies negative marking if configured.
    - Stores ExamAttempt and AttemptAnswer records.
    - Redirects to Instant Verification Report.
    """
    if request.method != 'POST':
        return redirect('portal:index')

    exam = get_object_or_404(Exam, id=exam_id)
    student_id = request.POST.get('student_id')
    student = get_object_or_404(Student, id=student_id)

    time_taken_seconds = 0
    try:
        time_taken_seconds = int(request.POST.get('time_taken_seconds', 0))
    except (ValueError, TypeError):
        time_taken_seconds = 0

    questions = exam.questions.all()
    total_questions = questions.count()

    correct_answers = 0
    wrong_answers = 0
    unattempted_answers = 0
    score_obtained = Decimal('0.00')
    max_score = Decimal('0.00')

    attempt_number = ExamAttempt.objects.filter(student=student, exam=exam).count() + 1

    # Create ExamAttempt record
    attempt = ExamAttempt.objects.create(
        exam=exam,
        student=student,
        attempt_number=attempt_number,
        completed_at=timezone.now(),
        time_taken_seconds=time_taken_seconds,
        total_questions=total_questions,
        is_completed=True,
    )

    answer_objects = []

    for question in questions:
        max_score += question.marks
        selected_option = request.POST.get(f'question_{question.id}')

        if selected_option and selected_option in ['A', 'B', 'C', 'D']:
            if selected_option == question.correct_option:
                is_correct = True
                marks_awarded = question.marks
                correct_answers += 1
                score_obtained += marks_awarded
            else:
                is_correct = False
                marks_awarded = -abs(question.negative_marks)
                wrong_answers += 1
                score_obtained += marks_awarded
        else:
            selected_option = None
            is_correct = False
            marks_awarded = Decimal('0.00')
            unattempted_answers += 1

        answer_objects.append(
            AttemptAnswer(
                attempt=attempt,
                question=question,
                selected_option=selected_option,
                is_correct=is_correct,
                marks_awarded=marks_awarded,
            )
        )

    # Bulk create answers
    AttemptAnswer.objects.bulk_create(answer_objects)

    # Floor score at 0 if desired (so score doesn't display negative)
    final_score = max(Decimal('0.00'), score_obtained)
    percentage = Decimal('0.00')
    if max_score > 0:
        percentage = round((final_score / max_score) * 100, 2)

    is_passed = percentage >= exam.passing_percentage

    # Update attempt summary
    attempt.correct_answers = correct_answers
    attempt.wrong_answers = wrong_answers
    attempt.unattempted_answers = unattempted_answers
    attempt.score_obtained = final_score
    attempt.max_score = max_score
    attempt.percentage = percentage
    attempt.is_passed = is_passed
    attempt.save()

    return redirect('portal:exam_result', attempt_id=attempt.id)


def exam_result(request, attempt_id):
    """
    Verification & Confirmation Report page.
    Displays:
    - Score breakdown & Pass/Fail status.
    - Question-by-question review:
      * User's selected option highlighted (green if right, red if wrong).
      * Correct option highlighted.
      * Detailed explanation of the question.
    - Unlimited retake link.
    """
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related('exam', 'student', 'student__student_class')
        .prefetch_related('answers__question'),
        id=attempt_id
    )

    # Order answers by question order
    answers = attempt.answers.select_related('question').order_by('question__order', 'question__id')

    # Get student's previous attempts for comparison
    all_attempts_for_exam = ExamAttempt.objects.filter(
        student=attempt.student,
        exam=attempt.exam
    ).order_by('attempt_number')

    context = {
        'attempt': attempt,
        'exam': attempt.exam,
        'student': attempt.student,
        'answers': answers,
        'all_attempts_for_exam': all_attempts_for_exam,
    }
    return render(request, 'portal/exam_result.html', context)


def attempt_result_pdf(request, attempt_id):
    """
    Downloads an official vector-crisp PDF scorecard for a student's exam attempt.
    Generated server-side via ReportLab (never blank, instant download, full question review).
    """
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related('exam', 'student', 'student__student_class')
        .prefetch_related('answers__question'),
        id=attempt_id
    )
    pdf_bytes = generate_attempt_result_pdf(attempt)
    exam_slug = slugify(attempt.exam.title) or 'exam'
    student_slug = slugify(attempt.student.name) or 'student'
    filename = f"{exam_slug}_{student_slug}_Report.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def student_history(request, student_id):
    """
    Public student history view:
    Shows all attempts made by a particular student, with links to full reports.
    """
    student = get_object_or_404(
        Student.objects.select_related('student_class'),
        id=student_id,
        is_active=True
    )
    attempts = student.attempts.select_related('exam').order_by('-started_at')

    context = {
        'student': student,
        'attempts': attempts,
    }
    return render(request, 'portal/student_history.html', context)


# ==============================================================================
# SUPERUSER / ADMIN CONTROL CENTER VIEWS
# ==============================================================================

def superuser_login_view(request):
    """Admin login page for the portal."""
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('portal:superuser_dashboard')

    if request.method == 'POST':
        form = SuperuserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser or user.is_staff:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('portal:superuser_dashboard')
            else:
                messages.error(request, "Access restricted to administrators only.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = SuperuserLoginForm()

    return render(request, 'portal/admin_login.html', {'form': form})


def superuser_logout_view(request):
    """Admin logout view."""
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('portal:index')


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def superuser_dashboard(request):
    """
    Superuser Executive Dashboard:
    Total classes, students, exams, attempts, and performance statistics.
    """
    total_classes = AcademicClass.objects.count()
    total_students = Student.objects.filter(is_active=True).count()
    total_exams = Exam.objects.filter(is_active=True).count()
    total_attempts = ExamAttempt.objects.count()

    recent_attempts = (
        ExamAttempt.objects.select_related('student', 'exam', 'student__student_class')
        .order_by('-started_at')[:15]
    )

    classes = AcademicClass.objects.annotate(
        student_count=Count('students', filter=Q(students__is_active=True)),
        exam_count=Count('exams', filter=Q(exams__is_active=True))
    )

    exams = Exam.objects.annotate(
        attempt_count=Count('attempts'),
        avg_score=Avg('attempts__score_obtained'),
        highest_score=Max('attempts__score_obtained')
    )

    context = {
        'total_classes': total_classes,
        'total_students': total_students,
        'total_exams': total_exams,
        'total_attempts': total_attempts,
        'recent_attempts': recent_attempts,
        'classes': classes,
        'exams': exams,
    }
    return render(request, 'portal/admin_dashboard.html', context)


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def superuser_students(request):
    """
    Superuser Student Directory:
    Search and filter students class-wise.
    Displays total attempts per student and links to their full audit profile.
    """
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

    context = {
        'classes': classes,
        'selected_class_id': selected_class_id,
        'search_query': search_query,
        'students': students,
    }
    return render(request, 'portal/admin_students.html', context)


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def superuser_student_detail(request, student_id):
    """
    Superuser Student Audit & History:
    Meets key requirement:
    'Like for the particular student that how many Exams attempt by that students,
    that list of that exam and report that everything should be visible to the Super user.'
    """
    student = get_object_or_404(
        Student.objects.select_related('student_class'),
        id=student_id
    )
    attempts = student.attempts.select_related('exam').order_by('-started_at')

    # Aggregate statistics for this student
    total_attempts = attempts.count()
    exams_attempted_distinct = attempts.values('exam').distinct().count()
    avg_percentage = attempts.aggregate(Avg('percentage'))['percentage__avg'] or 0
    passed_count = attempts.filter(is_passed=True).count()

    context = {
        'student': student,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'exams_attempted_distinct': exams_attempted_distinct,
        'avg_percentage': round(avg_percentage, 1),
        'passed_count': passed_count,
    }
    return render(request, 'portal/admin_student_detail.html', context)


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def superuser_exam_detail(request, exam_id):
    """
    Superuser Exam Analytics & Attempt Ledger:
    Shows all student attempts on a specific exam, leaderboard, and question list.
    """
    exam = get_object_or_404(
        Exam.objects.prefetch_related('classes', 'questions'),
        id=exam_id
    )
    attempts = (
        exam.attempts.select_related('student', 'student__student_class')
        .order_by('-score_obtained', 'time_taken_seconds')
    )

    total_attempts = attempts.count()
    avg_score = attempts.aggregate(Avg('score_obtained'))['score_obtained__avg'] or 0
    highest_score = attempts.aggregate(Max('score_obtained'))['score_obtained__max'] or 0

    context = {
        'exam': exam,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 2),
        'highest_score': highest_score,
        'questions': exam.questions.all().order_by('order', 'id'),
    }
    return render(request, 'portal/admin_exam_detail.html', context)


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def superuser_bulk_upload_students(request):
    """Bulk student CSV upload for a selected class."""
    if request.method == 'POST':
        form = BulkStudentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            academic_class = form.cleaned_data['academic_class']
            csv_file = form.cleaned_data['csv_file']
            created, updated, errors = import_students_from_csv(csv_file, academic_class)
            
            if created or updated:
                messages.success(
                    request,
                    f"Successfully processed students for {academic_class.name}: {created} added, {updated} updated."
                )
            if errors:
                for err in errors[:5]:
                    messages.error(request, err)
                if len(errors) > 5:
                    messages.error(request, f"...and {len(errors) - 5} more errors.")
            return redirect('portal:superuser_students')
    else:
        form = BulkStudentUploadForm()

    return render(request, 'portal/admin_bulk_upload_students.html', {'form': form})


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def superuser_bulk_upload_questions(request):
    """Bulk question CSV upload for a selected exam."""
    if request.method == 'POST':
        form = BulkQuestionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            exam = form.cleaned_data['exam']
            csv_file = form.cleaned_data['csv_file']
            created, errors = import_questions_from_csv(csv_file, exam)

            if created:
                messages.success(request, f"Successfully uploaded {created} questions to '{exam.title}'.")
            if errors:
                for err in errors[:5]:
                    messages.error(request, err)
                if len(errors) > 5:
                    messages.error(request, f"...and {len(errors) - 5} more errors.")
            return redirect('portal:superuser_exam_detail', exam_id=exam.id)
    else:
        form = BulkQuestionUploadForm()

    return render(request, 'portal/admin_bulk_upload_questions.html', {'form': form})


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def download_sample_student_csv_view(request):
    return generate_sample_student_csv()


@user_passes_test(is_superuser_or_staff, login_url='/admin-login/')
def download_sample_question_csv_view(request):
    return generate_sample_question_csv()
