from django import forms
from django.contrib.auth.forms import AuthenticationForm
from decimal import Decimal
from .models import AcademicClass, Subject, Student, Exam, Question


class SuperuserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter username',
            'autofocus': True,
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter password',
            'autocomplete': 'current-password'
        })
    )


class BulkStudentUploadForm(forms.Form):
    academic_class = forms.ModelChoiceField(
        queryset=AcademicClass.objects.filter(is_active=True),
        empty_label="-- Select Target Class --",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    csv_file = forms.FileField(
        label="Select CSV File",
        widget=forms.FileInput(attrs={'class': 'form-control form-control-lg', 'accept': '.csv'})
    )


class BulkQuestionUploadForm(forms.Form):
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all(),
        empty_label="-- Select Target Exam --",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    csv_file = forms.FileField(
        label="Select CSV File",
        widget=forms.FileInput(attrs={'class': 'form-control form-control-lg', 'accept': '.csv'})
    )


class BulkQuestionTextForm(forms.Form):
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.all(),
        empty_label="-- Select Target Exam --",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )
    default_marks = forms.DecimalField(
        initial=Decimal('1.00'),
        decimal_places=2,
        max_digits=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'})
    )
    default_negative_marks = forms.DecimalField(
        initial=Decimal('0.00'),
        decimal_places=2,
        max_digits=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05'})
    )
    raw_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control font-monospace',
            'rows': 16,
            'placeholder': (
                "Paste your question paper text here, for example:\n\n"
                "1. What is the unit of electric current?\n"
                "A) Volt\n"
                "B) Ampere\n"
                "C) Ohm\n"
                "D) Watt\n"
                "Ans: B\n"
                "Explanation: Ampere is the SI unit of current.\n\n"
                "2. Which planet is known as the Red Planet?\n"
                "A) Earth\n"
                "B) Mars\n"
                "C) Jupiter\n"
                "D) Venus\n"
                "Ans: B\n"
                "Explanation: Mars appears reddish due to iron oxide on its surface."
            )
        })
    )


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['student_class', 'roll_number', 'name', 'phone', 'email', 'is_active']
        widgets = {
            'student_class': forms.Select(attrs={'class': 'form-select'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ARO-101'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Rahul Sharma'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'e.g. rahul@example.com'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AcademicClassForm(forms.ModelForm):
    class Meta:
        model = AcademicClass
        fields = ['name', 'code', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Class 10 - Batch A'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. C10-A'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['academic_class', 'name', 'code', 'description', 'is_active']
        widgets = {
            'academic_class': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mathematics, Science, English'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MATH, SCI, ENG'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes or syllabus'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'title', 'code', 'classes', 'subject', 'duration_minutes', 
            'passing_percentage', 'negative_marking', 'shuffle_questions',
            'is_active', 'description', 'instructions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Science Mock Test 1'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MT-SCI-01'}),
            'classes': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4, 'id': 'id_classes'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_subject',
                'placeholder': 'Select or type subject...',
                'autocomplete': 'off'
            }),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'passing_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0, 'max': 100}),
            'negative_marking': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05', 'min': 0}),
            'shuffle_questions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def clean_subject(self):
        subject = self.cleaned_data.get('subject', '').strip()
        if not subject:
            raise forms.ValidationError("Please select or enter a subject for this mock test.")
        return subject


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'exam', 'order', 'question_text', 'question_image', 
            'option_a', 'option_b', 'option_c', 'option_d',
            'correct_option', 'marks', 'negative_marks', 'explanation'
        ]
        widgets = {
            'exam': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'question_image': forms.FileInput(attrs={'class': 'form-control'}),
            'option_a': forms.TextInput(attrs={'class': 'form-control'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_option': forms.Select(attrs={'class': 'form-select'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'negative_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.05'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
