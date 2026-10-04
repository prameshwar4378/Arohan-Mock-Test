from django.db import models
from django.utils import timezone
from decimal import Decimal


class AcademicClass(models.Model):
    """
    Represents an academic class/standard/batch (e.g., 'Class 10 - Batch A', 'NEET Dropper').
    """
    name = models.CharField(max_length=120, unique=True, help_text="Name of the class/batch")
    code = models.CharField(max_length=50, blank=True, help_text="Short code or identifier (e.g. C10-A)")
    description = models.TextField(blank=True, help_text="Optional description or notes about this class")
    is_active = models.BooleanField(default=True, help_text="Active classes will appear in the portal")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Class / Batch"
        verbose_name_plural = "Classes / Batches"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_students(self):
        return self.students.filter(is_active=True).count()

    @property
    def total_exams(self):
        return self.exams.filter(is_active=True).count()

    @property
    def total_subjects(self):
        return self.subjects.filter(is_active=True).count()


class Subject(models.Model):
    """
    Represents an academic subject taught in a class (e.g. Mathematics, Science, English, Marathi).
    Teachers can schedule mock tests subject-wise under each class.
    """
    academic_class = models.ForeignKey(
        AcademicClass,
        on_delete=models.CASCADE,
        related_name='subjects',
        verbose_name="Class"
    )
    name = models.CharField(max_length=120, help_text="Subject Name (e.g., Mathematics, Science, Physics)")
    code = models.CharField(max_length=50, blank=True, help_text="Short Subject Code (e.g., MATH, SCI)")
    description = models.TextField(blank=True, help_text="Optional description or syllabus")
    is_active = models.BooleanField(default=True, help_text="Active subjects are available for scheduling")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        unique_together = ('academic_class', 'name')
        ordering = ['academic_class__name', 'name']

    def __str__(self):
        return f"{self.name} ({self.academic_class.name})"

    @property
    def exams_count(self):
        return self.academic_class.exams.filter(subject__iexact=self.name, is_active=True).count()


class Student(models.Model):
    """
    Represents a student enrolled in a class.
    Students do not have passwords/accounts; they pick their class & name on the portal.
    """
    student_class = models.ForeignKey(
        AcademicClass,
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name="Class"
    )
    name = models.CharField(max_length=150, help_text="Student's full name")
    roll_number = models.CharField(max_length=50, help_text="Roll number or student ID")
    phone = models.CharField(max_length=25, blank=True, help_text="Optional contact number")
    email = models.EmailField(blank=True, help_text="Optional email address")
    is_active = models.BooleanField(default=True, help_text="Active students can take exams")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"
        unique_together = ('student_class', 'roll_number')
        ordering = ['student_class__name', 'name']

    def __str__(self):
        return f"{self.name} (Roll: {self.roll_number}) - {self.student_class.name}"

    @property
    def total_attempts_count(self):
        return self.attempts.count()

    @property
    def passed_attempts_count(self):
        return self.attempts.filter(is_passed=True).count()

    @property
    def latest_attempt(self):
        return self.attempts.order_by('-started_at').first()


class Exam(models.Model):
    """
    Represents an MCQ Mock Test created by the superuser.
    Can be assigned to one or more classes.
    """
    title = models.CharField(max_length=255, help_text="Title of the mock test (e.g. Science Mock Test 1)")
    code = models.CharField(max_length=50, blank=True, help_text="Exam code (e.g., MT-SCI-01)")
    classes = models.ManyToManyField(
        AcademicClass,
        related_name='exams',
        help_text="Select the class(es) eligible to take this exam"
    )
    subject = models.CharField(max_length=100, blank=True, help_text="Subject or Category (e.g., Mathematics, Physics)")
    description = models.TextField(blank=True, help_text="Short description or syllabus of the exam")
    instructions = models.TextField(
        blank=True,
        default=(
            "1. All questions are Multiple Choice Questions (MCQ).\n"
            "2. Select the most appropriate option for each question.\n"
            "3. You can review and change your answers before final submission.\n"
            "4. There is no restriction to attempt the exam; you can retake it anytime.\n"
            "5. After submitting, your detailed result and verification report will be displayed immediately."
        ),
        help_text="Instructions displayed to students before starting"
    )
    duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Duration in minutes. Enter 0 for unlimited time."
    )
    passing_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('40.00'),
        help_text="Minimum percentage required to pass"
    )
    negative_marking = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Default negative marks deducted per wrong question (e.g. 0.25 or 0)"
    )
    shuffle_questions = models.BooleanField(
        default=False,
        help_text="If enabled, questions will appear in randomized order for each attempt"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active exams are visible on the public portal"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mock Test / Exam"
        verbose_name_plural = "Mock Tests / Exams"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.subject or 'General'})"

    @property
    def total_questions_count(self):
        return self.questions.count()

    @property
    def total_marks(self):
        return sum(q.marks for q in self.questions.all())

    @property
    def total_attempts_count(self):
        return self.attempts.count()


class Question(models.Model):
    """
    Individual MCQ question under an Exam.
    Contains Question text, 4 Options, Correct Option, Marks, Negative Marks, and Detailed Explanation.
    """
    OPTION_CHOICES = [
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Mock Test"
    )
    order = models.PositiveIntegerField(default=1, help_text="Display order sequence")
    question_text = models.TextField(help_text="Question text or prompt")
    question_image = models.ImageField(upload_to='questions/', blank=True, null=True, help_text="Optional diagram/image")
    
    option_a = models.TextField(verbose_name="Option A")
    option_b = models.TextField(verbose_name="Option B")
    option_c = models.TextField(verbose_name="Option C")
    option_d = models.TextField(verbose_name="Option D")
    
    correct_option = models.CharField(
        max_length=1,
        choices=OPTION_CHOICES,
        help_text="The correct answer option (A, B, C, or D)"
    )
    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Marks awarded for correct answer"
    )
    negative_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Marks deducted for incorrect answer (0 for no penalty)"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Detailed solution/explanation revealed after test submission"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Question"
        verbose_name_plural = "Questions"
        ordering = ['order', 'id']

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:60]}... ({self.exam.title})"

    def get_option_text(self, option_letter):
        mapping = {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }
        return mapping.get(option_letter, '')


class ExamAttempt(models.Model):
    """
    Records an individual student's attempt at an exam.
    Students can attempt the same exam multiple times; each attempt has its own record and attempt_number.
    """
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.PositiveIntegerField(default=1, help_text="Attempt sequence number (1st, 2nd, etc.)")
    
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(default=0)
    
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    unattempted_answers = models.PositiveIntegerField(default=0)
    
    score_obtained = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    max_score = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    
    is_passed = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Exam Attempt"
        verbose_name_plural = "Exam Attempts"
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.name} - {self.exam.title} (Attempt #{self.attempt_number}) - Score: {self.score_obtained}/{self.max_score}"

    @property
    def formatted_time_taken(self):
        mins = self.time_taken_seconds // 60
        secs = self.time_taken_seconds % 60
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"

    @property
    def accuracy_percentage(self):
        attempted = self.correct_answers + self.wrong_answers
        if attempted > 0:
            return round((self.correct_answers / attempted) * 100, 1)
        return 0.0

    @property
    def grade(self):
        pct = float(self.percentage)
        if pct >= 90:
            return 'A+'
        elif pct >= 80:
            return 'A'
        elif pct >= 70:
            return 'B+'
        elif pct >= 60:
            return 'B'
        elif pct >= 50:
            return 'C'
        elif pct >= 40:
            return 'D'
        return 'E'

    @property
    def grade_title(self):
        pct = float(self.percentage)
        if pct >= 90:
            return 'Outstanding'
        elif pct >= 80:
            return 'Excellent'
        elif pct >= 70:
            return 'Very Good'
        elif pct >= 60:
            return 'Good'
        elif pct >= 50:
            return 'Satisfactory'
        elif pct >= 40:
            return 'Pass'
        return 'Needs Practice'

    @property
    def grade_badge_class(self):
        pct = float(self.percentage)
        if pct >= 80:
            return 'grade-gold'
        elif pct >= 60:
            return 'grade-silver'
        elif pct >= 40:
            return 'grade-bronze'
        return 'grade-practice'


class AttemptAnswer(models.Model):
    """
    Stores the student's answer for each question in a specific attempt.
    """
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempt_answers')
    selected_option = models.CharField(max_length=1, blank=True, null=True, help_text="A, B, C, D or None if skipped")
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = "Attempt Answer"
        verbose_name_plural = "Attempt Answers"
        unique_together = ('attempt', 'question')

    def __str__(self):
        status = "Correct" if self.is_correct else ("Incorrect" if self.selected_option else "Skipped")
        return f"{self.attempt} - Q{self.question.id} ({status})"
