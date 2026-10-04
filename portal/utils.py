import csv
import io
import re
from decimal import Decimal
from django.http import HttpResponse
from .models import AcademicClass, Student, Exam, Question


def generate_sample_student_csv():
    """Generates a downloadable sample CSV for bulk student upload."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_students_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['roll_number', 'name', 'phone', 'email'])
    writer.writerow(['ARO-101', 'Aarav Sharma', '9876543210', 'aarav@example.com'])
    writer.writerow(['ARO-102', 'Priya Patel', '9876543211', 'priya@example.com'])
    writer.writerow(['ARO-103', 'Rohan Verma', '9876543212', 'rohan@example.com'])
    writer.writerow(['ARO-104', 'Ananya Gupta', '9876543213', 'ananya@example.com'])
    writer.writerow(['ARO-105', 'Kabir Singh', '9876543214', 'kabir@example.com'])
    return response


def generate_sample_question_csv():
    """Generates a downloadable sample CSV for bulk question upload."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_questions_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['order', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option', 'marks', 'negative_marks', 'explanation'])
    writer.writerow([
        1,
        'What is the chemical formula for water?',
        'H2O',
        'CO2',
        'NaCl',
        'CH4',
        'A',
        1.0,
        0.25,
        'Water is composed of two hydrogen atoms and one oxygen atom bonded together (H2O).'
    ])
    writer.writerow([
        2,
        'Which planet is known as the Red Planet?',
        'Earth',
        'Mars',
        'Jupiter',
        'Venus',
        'B',
        1.0,
        0.25,
        'Mars is called the Red Planet because iron minerals in the Martian soil oxidize or rust.'
    ])
    writer.writerow([
        3,
        'What is the powerhouse of the cell?',
        'Nucleus',
        'Ribosome',
        'Mitochondria',
        'Endoplasmic Reticulum',
        'C',
        1.0,
        0.0,
        'Mitochondria generate most of the chemical energy needed to power the cell biochemical reactions.'
    ])
    return response


def import_students_from_csv(file, academic_class):
    """
    Imports students from an uploaded CSV file for a given AcademicClass.
    Returns: (created_count, updated_count, errors_list)
    """
    created_count = 0
    updated_count = 0
    errors = []

    try:
        decoded_file = file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)
        
        # Normalize header keys
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames if f]

        for row_idx, row in enumerate(reader, start=2):
            roll_number = row.get('roll_number', '').strip()
            name = row.get('name', '').strip()
            phone = row.get('phone', '').strip()
            email = row.get('email', '').strip()

            if not roll_number or not name:
                errors.append(f"Row {row_idx}: 'roll_number' and 'name' are required fields.")
                continue

            student, created = Student.objects.update_or_create(
                student_class=academic_class,
                roll_number=roll_number,
                defaults={
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

    except Exception as e:
        errors.append(f"File reading error: {str(e)}")

    return created_count, updated_count, errors


def import_questions_from_csv(file, exam):
    """
    Imports questions from an uploaded CSV file for a given Exam.
    Returns: (created_count, errors_list)
    """
    created_count = 0
    errors = []

    try:
        decoded_file = file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)
        reader.fieldnames = [f.strip().lower() for f in reader.fieldnames if f]

        current_max_order = Question.objects.filter(exam=exam).count()

        for row_idx, row in enumerate(reader, start=2):
            q_text = row.get('question_text', '').strip()
            opt_a = row.get('option_a', '').strip()
            opt_b = row.get('option_b', '').strip()
            opt_c = row.get('option_c', '').strip()
            opt_d = row.get('option_d', '').strip()
            correct = row.get('correct_option', '').strip().upper()
            explanation = row.get('explanation', '').strip()

            if not q_text or not opt_a or not opt_b or not opt_c or not opt_d:
                errors.append(f"Row {row_idx}: Question text and all 4 options (A, B, C, D) are required.")
                continue

            if correct not in ['A', 'B', 'C', 'D']:
                errors.append(f"Row {row_idx}: Invalid correct option '{correct}'. Must be A, B, C, or D.")
                continue

            try:
                order_val = int(row.get('order', current_max_order + 1))
            except (ValueError, TypeError):
                order_val = current_max_order + 1

            try:
                marks_val = Decimal(str(row.get('marks', 1.0)).strip() or '1.0')
            except Exception:
                marks_val = Decimal('1.00')

            try:
                neg_marks_val = Decimal(str(row.get('negative_marks', 0.0)).strip() or '0.0')
            except Exception:
                neg_marks_val = Decimal('0.00')

            Question.objects.create(
                exam=exam,
                order=order_val,
                question_text=q_text,
                option_a=opt_a,
                option_b=opt_b,
                option_c=opt_c,
                option_d=opt_d,
                correct_option=correct,
                marks=marks_val,
                negative_marks=neg_marks_val,
                explanation=explanation,
            )
            created_count += 1
            current_max_order += 1

    except Exception as e:
        errors.append(f"File reading error: {str(e)}")

def format_questions_to_text(questions):
    """
    Serializes a queryset or iterable of Question objects into the standard
    Smart Parser text format so supervisors can easily inspect, edit, update,
    or append questions in the bulk text editor.
    """
    output_blocks = []
    for idx, q in enumerate(questions, start=1):
        lines = []
        q_text = (q.question_text or '').strip()
        lines.append(f"{idx}. {q_text}")
        lines.append(f"A) {(q.option_a or '').strip()}")
        lines.append(f"B) {(q.option_b or '').strip()}")
        lines.append(f"C) {(q.option_c or '').strip()}")
        lines.append(f"D) {(q.option_d or '').strip()}")
        lines.append(f"Ans: {(q.correct_option or 'A').strip().upper()}")

        if q.explanation and q.explanation.strip():
            lines.append(f"Explanation: {q.explanation.strip()}")

        marks = getattr(q, 'marks', None)
        if marks is not None:
            marks_str = f"{marks:.2f}".rstrip('0').rstrip('.') if isinstance(marks, (Decimal, float)) else str(marks)
            lines.append(f"Marks: {marks_str}")

        neg_marks = getattr(q, 'negative_marks', None)
        if neg_marks is not None:
            neg_str = f"{neg_marks:.2f}".rstrip('0').rstrip('.') if isinstance(neg_marks, (Decimal, float)) else str(neg_marks)
            lines.append(f"Negative: {neg_str}")

        output_blocks.append("\n".join(lines))

    return "\n\n".join(output_blocks)


def parse_bulk_question_text(raw_text, default_marks=Decimal('1.00'), default_negative=Decimal('0.00')):
    """
    Intelligent bulk text parser for supervisor question papers.
    Parses questions copied from Word / PDFs / Textbooks.
    
    Supports patterns:
    - Question start:
        1. Question text
        Q1. Question text
        Question 1: Question text
    - Options:
        A) ... or A. ... or (A) ...
        B) ... or B. ... or (B) ...
        C) ... or C. ... or (C) ...
        D) ... or D. ... or (D) ...
    - Correct Answer:
        Answer: B or Ans: B or Correct: B or Key: B
    - Explanation:
        Explanation: ... or Solution: ... or Sol: ...
    - Marks / Negative:
        Marks: 2.0
        Negative: 0.5

    Returns: list of dicts with:
    [
        {
            'order': int,
            'question_text': str,
            'option_a': str,
            'option_b': str,
            'option_c': str,
            'option_d': str,
            'correct_option': str,
            'marks': Decimal,
            'negative_marks': Decimal,
            'explanation': str,
        },
        ...
    ], errors_list
    """
    questions = []
    errors = []

    lines = raw_text.strip().splitlines()
    if not lines:
        return [], ["Input text is empty."]

    current_q = None
    current_state = None  # 'question', 'option_a', 'option_b', 'option_c', 'option_d', 'explanation'

    # Regex patterns
    q_start_regex = re.compile(r'^(?:Q(?:uestion)?\s*[\.\:\-]?\s*(\d+)[\.\)\:\-]?|\b(\d+)[\.\)\:\-])\s*(.*)$', re.IGNORECASE)
    opt_regex = re.compile(r'^(?:\(?([A-Da-d])\)|\b([A-Da-d])[\.\:\-\)])\s*(.*)$')
    ans_regex = re.compile(r'^(?:ans(?:wer)?|correct(?:\s*option)?|key)\s*[\:\-\=]?\s*\(?([A-Da-d])\)?', re.IGNORECASE)
    exp_regex = re.compile(r'^(?:explanation|solution|exp|sol|reason)\s*[\:\-\=]?\s*(.*)$', re.IGNORECASE)
    marks_regex = re.compile(r'^marks?\s*[\:\-\=]?\s*([\d\.]+)', re.IGNORECASE)
    neg_regex = re.compile(r'^(?:negative(?:\s*marks?)?|neg)\s*[\:\-\=]?\s*([\d\.]+)', re.IGNORECASE)

    def save_current_question():
        nonlocal current_q
        if current_q:
            # Validate required fields
            q_num = current_q.get('order', len(questions) + 1)
            q_text = current_q.get('question_text', '').strip()
            opt_a = current_q.get('option_a', '').strip()
            opt_b = current_q.get('option_b', '').strip()
            opt_c = current_q.get('option_c', '').strip()
            opt_d = current_q.get('option_d', '').strip()
            correct = current_q.get('correct_option', '').strip().upper()

            if not q_text:
                errors.append(f"Question #{q_num}: Missing question statement.")
                return
            if not (opt_a and opt_b and opt_c and opt_d):
                errors.append(f"Question #{q_num} ('{q_text[:30]}...'): All 4 options (A, B, C, D) are required.")
                return
            if correct not in ['A', 'B', 'C', 'D']:
                errors.append(f"Question #{q_num} ('{q_text[:30]}...'): Missing or invalid correct answer (must be A, B, C, or D).")
                return

            current_q['question_text'] = q_text
            current_q['option_a'] = opt_a
            current_q['option_b'] = opt_b
            current_q['option_c'] = opt_c
            current_q['option_d'] = opt_d
            current_q['correct_option'] = correct
            current_q['explanation'] = current_q.get('explanation', '').strip()
            questions.append(current_q)

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        # Check for Question Start
        q_match = q_start_regex.match(line)
        if q_match:
            save_current_question()
            q_order = q_match.group(1) or q_match.group(2)
            try:
                order_num = int(q_order) if q_order else len(questions) + 1
            except ValueError:
                order_num = len(questions) + 1

            rest_text = q_match.group(3).strip()
            current_q = {
                'order': order_num,
                'question_text': rest_text,
                'option_a': '',
                'option_b': '',
                'option_c': '',
                'option_d': '',
                'correct_option': '',
                'marks': default_marks,
                'negative_marks': default_negative,
                'explanation': '',
            }
            current_state = 'question'
            continue

        if not current_q:
            # First line without explicit number: initialize as Q1
            current_q = {
                'order': len(questions) + 1,
                'question_text': line,
                'option_a': '',
                'option_b': '',
                'option_c': '',
                'option_d': '',
                'correct_option': '',
                'marks': default_marks,
                'negative_marks': default_negative,
                'explanation': '',
            }
            current_state = 'question'
            continue

        # Check for Answer
        ans_match = ans_regex.match(line)
        if ans_match:
            current_q['correct_option'] = ans_match.group(1).upper()
            current_state = 'answer'
            continue

        # Check for Explanation
        exp_match = exp_regex.match(line)
        if exp_match:
            current_q['explanation'] = exp_match.group(1).strip()
            current_state = 'explanation'
            continue

        # Check for Marks
        marks_match = marks_regex.match(line)
        if marks_match:
            try:
                current_q['marks'] = Decimal(marks_match.group(1))
            except Exception:
                pass
            continue

        # Check for Negative Marks
        neg_match = neg_regex.match(line)
        if neg_match:
            try:
                current_q['negative_marks'] = Decimal(neg_match.group(1))
            except Exception:
                pass
            continue

        # Check for Options (A, B, C, D)
        opt_match = opt_regex.match(line)
        if opt_match:
            opt_letter = (opt_match.group(1) or opt_match.group(2)).upper()
            opt_content = opt_match.group(3).strip()
            if opt_letter == 'A':
                current_q['option_a'] = opt_content
                current_state = 'option_a'
            elif opt_letter == 'B':
                current_q['option_b'] = opt_content
                current_state = 'option_b'
            elif opt_letter == 'C':
                current_q['option_c'] = opt_content
                current_state = 'option_c'
            elif opt_letter == 'D':
                current_q['option_d'] = opt_content
                current_state = 'option_d'
            continue

        # Continuation lines based on current state
        if current_state == 'question':
            current_q['question_text'] += ("\n" + line) if current_q['question_text'] else line
        elif current_state == 'option_a':
            current_q['option_a'] += (" " + line)
        elif current_state == 'option_b':
            current_q['option_b'] += (" " + line)
        elif current_state == 'option_c':
            current_q['option_c'] += (" " + line)
        elif current_state == 'option_d':
            current_q['option_d'] += (" " + line)
        elif current_state == 'explanation':
            current_q['explanation'] += ("\n" + line) if current_q['explanation'] else line

    # Save the last question
    save_current_question()

    return questions, errors
