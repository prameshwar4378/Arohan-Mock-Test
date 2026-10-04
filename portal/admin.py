from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import AcademicClass, Subject, Student, Exam, Question, ExamAttempt, AttemptAnswer


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = (
        ('order', 'correct_option'),
        'question_text',
        ('option_a', 'option_b'),
        ('option_c', 'option_d'),
        ('marks', 'negative_marks'),
        'explanation',
    )


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct', 'marks_awarded')
    can_delete = False


@admin.register(AcademicClass)
class AcademicClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'total_students_count', 'total_exams_count', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')

    def total_students_count(self, obj):
        return obj.students.count()
    total_students_count.short_description = "Enrolled Students"

    def total_exams_count(self, obj):
        return obj.exams.count()
    total_exams_count.short_description = "Exams Assigned"


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_class', 'code', 'exams_count_display', 'is_active', 'created_at')
    list_filter = ('academic_class', 'is_active')
    search_fields = ('name', 'code', 'academic_class__name')

    def exams_count_display(self, obj):
        return obj.exams_count
    exams_count_display.short_description = "Scheduled Exams"


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'name', 'student_class', 'phone', 'total_attempts_display', 'view_history_button', 'is_active')
    list_filter = ('student_class', 'is_active')
    search_fields = ('name', 'roll_number', 'phone', 'email')
    ordering = ('student_class', 'roll_number')

    def total_attempts_display(self, obj):
        count = obj.attempts.count()
        return format_html('<span class="badge badge-info" style="font-size:0.9rem;">{} Attempts</span>', count)
    total_attempts_display.short_description = "Exams Attempted"

    def view_history_button(self, obj):
        url = reverse('portal:superuser_student_detail', args=[obj.id])
        return format_html('<a class="button btn btn-sm btn-primary" href="{}" target="_blank">View History</a>', url)
    view_history_button.short_description = "Attempt History"


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'subject', 'duration_minutes', 'questions_count', 'attempts_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'subject', 'classes')
    search_fields = ('title', 'code', 'subject')
    filter_horizontal = ('classes',)
    inlines = [QuestionInline]

    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = "Total Questions"

    def attempts_count(self, obj):
        count = obj.attempts.count()
        url = reverse('portal:superuser_exam_detail', args=[obj.id])
        return format_html('<a href="{}" style="font-weight:bold;">{} attempts</a>', url, count)
    attempts_count.short_description = "Total Attempts"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam', 'order', 'short_question_text', 'correct_option', 'marks', 'negative_marks')
    list_filter = ('exam', 'correct_option')
    search_fields = ('question_text', 'explanation')
    ordering = ('exam', 'order', 'id')

    def short_question_text(self, obj):
        return obj.question_text[:75] + ("..." if len(obj.question_text) > 75 else "")
    short_question_text.short_description = "Question Text"


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'student', 'exam', 'attempt_number', 
        'score_display', 'percentage_display', 'status_badge', 
        'started_at', 'view_report_button'
    )
    list_filter = ('is_passed', 'exam', 'student__student_class')
    search_fields = ('student__name', 'student__roll_number', 'exam__title')
    readonly_fields = (
        'exam', 'student', 'attempt_number', 'started_at', 'completed_at',
        'time_taken_seconds', 'total_questions', 'correct_answers', 
        'wrong_answers', 'unattempted_answers', 'score_obtained', 
        'max_score', 'percentage', 'is_passed', 'is_completed'
    )
    inlines = [AttemptAnswerInline]
    ordering = ('-started_at',)

    def score_display(self, obj):
        return f"{obj.score_obtained} / {obj.max_score}"
    score_display.short_description = "Score"

    def percentage_display(self, obj):
        return f"{obj.percentage}%"
    percentage_display.short_description = "Percentage"

    def status_badge(self, obj):
        if obj.is_passed:
            return format_html('<span style="color:#10b981; font-weight:bold;">Passed</span>')
        return format_html('<span style="color:#ef4444; font-weight:bold;">Failed</span>')
    status_badge.short_description = "Result"

    def view_report_button(self, obj):
        url = reverse('portal:exam_result', args=[obj.id])
        return format_html('<a class="button btn btn-sm btn-success" href="{}" target="_blank">Full Report</a>', url)
    view_report_button.short_description = "Report"
