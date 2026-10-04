from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone
import json

from portal.models import AcademicClass, Subject, Student, Exam, Question, ExamAttempt, AttemptAnswer
from portal.utils import parse_bulk_question_text, format_questions_to_text


class MockTestPortalTests(TestCase):
    def setUp(self):
        self.client = Client()
        User = get_user_model()
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

        # Academic Class
        self.academic_class = AcademicClass.objects.create(
            name="Class 10 - Science",
            code="C10-SCI"
        )

        # Student
        self.student = Student.objects.create(
            student_class=self.academic_class,
            name="Rohan Sharma",
            roll_number="ARO-001",
            phone="9998887770",
            email="rohan@example.com"
        )

        # Exam
        self.exam = Exam.objects.create(
            title="Science Unit Test 1",
            subject="Science",
            duration_minutes=15,
            passing_percentage=Decimal('50.00'),
            negative_marking=Decimal('0.25')
        )
        self.exam.classes.add(self.academic_class)

        # Question 1 (Correct: A)
        self.q1 = Question.objects.create(
            exam=self.exam,
            order=1,
            question_text="What is the chemical formula of water?",
            option_a="H2O",
            option_b="CO2",
            option_c="NaCl",
            option_d="CH4",
            correct_option="A",
            marks=Decimal('2.00'),
            negative_marks=Decimal('0.50'),
            explanation="Water is H2O."
        )

        # Question 2 (Correct: B)
        self.q2 = Question.objects.create(
            exam=self.exam,
            order=2,
            question_text="Which planet is the Red Planet?",
            option_a="Earth",
            option_b="Mars",
            option_c="Jupiter",
            option_d="Venus",
            correct_option="B",
            marks=Decimal('2.00'),
            negative_marks=Decimal('0.50'),
            explanation="Mars is known as the Red Planet."
        )

    def test_public_index_view(self):
        """Test landing page renders classes and portal elements."""
        response = self.client.get(reverse('portal:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Arohan Academy English School")
        self.assertContains(response, "Class 10 - Science")

    def test_api_class_data(self):
        """Test AJAX endpoint returns JSON of students and exams."""
        response = self.client.get(reverse('portal:get_class_data', args=[self.academic_class.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['students']), 1)
        self.assertEqual(data['students'][0]['name'], "Rohan Sharma")
        self.assertEqual(len(data['exams']), 1)
        self.assertEqual(data['exams'][0]['title'], "Science Unit Test 1")

    def test_exam_instructions(self):
        """Test exam instructions page loads with student verification."""
        url = reverse('portal:exam_instruction', args=[self.exam.id])
        response = self.client.get(f"{url}?student_id={self.student.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rohan Sharma")
        self.assertContains(response, "Attempt #1")
        self.assertContains(response, "Start Mock Test Now")

    def test_exam_take_view(self):
        """Test CBT runner view displays questions and options."""
        url = reverse('portal:exam_take', args=[self.exam.id])
        response = self.client.get(f"{url}?student_id={self.student.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is the chemical formula of water?")
        self.assertContains(response, "H2O")
        self.assertContains(response, "Question Palette")

    def test_exam_submission_and_instant_verification(self):
        """
        Test submitting exam:
        Q1 answered correctly (A) -> +2.0 marks
        Q2 answered incorrectly (C instead of B) -> -0.5 marks
        Total score = 1.5 / 4.0 = 37.5% -> Failed (passing is 50%)
        """
        post_data = {
            'student_id': self.student.id,
            'time_taken_seconds': 120,
            f'question_{self.q1.id}': 'A',  # Correct
            f'question_{self.q2.id}': 'C',  # Wrong
        }
        submit_url = reverse('portal:exam_submit', args=[self.exam.id])
        response = self.client.post(submit_url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)
        self.assertEqual(attempt.attempt_number, 1)
        self.assertEqual(attempt.correct_answers, 1)
        self.assertEqual(attempt.wrong_answers, 1)
        self.assertEqual(attempt.unattempted_answers, 0)
        self.assertEqual(attempt.score_obtained, Decimal('1.50'))
        self.assertEqual(attempt.max_score, Decimal('4.00'))
        self.assertEqual(attempt.percentage, Decimal('37.50'))
        self.assertFalse(attempt.is_passed)

        # Check Verification Report elements
        self.assertContains(response, "1.50")
        self.assertContains(response, "NEEDS PRACTICE")
        self.assertContains(response, "Your Answer &bull; Correct")
        self.assertContains(response, "Your Answer &bull; Incorrect")
        self.assertContains(response, "Water is H2O.")

    def test_unlimited_multi_attempts(self):
        """
        Test that a student can take the same exam multiple times,
        incrementing attempt_number and storing separate records.
        """
        # Attempt 1 (0 / 4)
        post_data_1 = {
            'student_id': self.student.id,
            'time_taken_seconds': 60,
            f'question_{self.q1.id}': 'B',  # wrong
            f'question_{self.q2.id}': 'A',  # wrong
        }
        self.client.post(reverse('portal:exam_submit', args=[self.exam.id]), post_data_1)

        # Attempt 2 (4 / 4 - 100%)
        post_data_2 = {
            'student_id': self.student.id,
            'time_taken_seconds': 45,
            f'question_{self.q1.id}': 'A',  # correct
            f'question_{self.q2.id}': 'B',  # correct
        }
        self.client.post(reverse('portal:exam_submit', args=[self.exam.id]), post_data_2)

        attempts = ExamAttempt.objects.filter(student=self.student, exam=self.exam).order_by('attempt_number')
        self.assertEqual(attempts.count(), 2)
        self.assertEqual(attempts[0].attempt_number, 1)
        self.assertEqual(attempts[0].score_obtained, Decimal('0.00'))
        self.assertFalse(attempts[0].is_passed)

        self.assertEqual(attempts[1].attempt_number, 2)
        self.assertEqual(attempts[1].score_obtained, Decimal('4.00'))
        self.assertEqual(attempts[1].percentage, Decimal('100.00'))
        self.assertTrue(attempts[1].is_passed)

    def test_supervisor_login_and_dashboard(self):
        """Test dedicated supervisor login and dashboard access."""
        # Anonymous access redirects to login
        resp = self.client.get(reverse('portal:supervisor_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('portal:supervisor_login'), resp.url)

        # Login page renders
        login_page_resp = self.client.get(reverse('portal:supervisor_login'))
        self.assertEqual(login_page_resp.status_code, 200)
        self.assertContains(login_page_resp, "Supervisor Portal")

        # Perform login
        post_login = self.client.post(reverse('portal:supervisor_login'), {
            'username': 'admin',
            'password': 'admin123'
        }, follow=True)
        self.assertEqual(post_login.status_code, 200)
        self.assertContains(post_login, "Supervisor Executive Dashboard")

    def test_supervisor_student_audit_detail(self):
        """Test supervisor can audit a student and see all attempts."""
        self.client.login(username='admin', password='admin123')
        
        # Create an attempt
        ExamAttempt.objects.create(
            exam=self.exam,
            student=self.student,
            attempt_number=1,
            score_obtained=Decimal('4.00'),
            max_score=Decimal('4.00'),
            percentage=Decimal('100.00'),
            is_passed=True
        )

        audit_url = reverse('portal:supervisor_student_detail', args=[self.student.id])
        resp = self.client.get(audit_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Rohan Sharma")
        self.assertContains(resp, "ARO-001")
        self.assertContains(resp, "Attempt #1")
        self.assertContains(resp, "100.0%")

    def test_smart_bulk_question_parser_and_save(self):
        """Test parsing raw question paper text and bulk saving to database."""
        raw_text = """
        1. What is the powerhouse of the cell?
        A) Nucleus
        B) Ribosome
        C) Mitochondria
        D) Golgi body
        Ans: C
        Explanation: Mitochondria generate ATP.
        Marks: 2.0
        Negative: 0.5

        2. What is H2O?
        (A) Hydrogen peroxide
        (B) Water
        (C) Acid
        (D) Salt
        Answer: B
        Solution: H2O is water.
        """
        parsed, errors = parse_bulk_question_text(raw_text)
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['correct_option'], 'C')
        self.assertEqual(parsed[1]['correct_option'], 'B')

        # Test POST saving via supervisor bulk questions view
        self.client.login(username='admin', password='admin123')
        save_post_data = {
            'action_type': 'save_text_questions',
            'target_exam_id': self.exam.id,
            'questions_json': json.dumps([
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
                } for q in parsed
            ])
        }
        resp = self.client.post(reverse('portal:supervisor_bulk_questions'), save_post_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Exam should now have 2 initial + 2 bulk added = 4 questions
        self.assertEqual(self.exam.questions.count(), 4)

    def test_sample_csv_downloads(self):
        """Test downloading sample CSV files."""
        self.client.login(username='admin', password='admin123')
        
        # Student CSV
        resp = self.client.get(reverse('portal:download_sample_student_csv'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('roll_number,name,phone,email', resp.content.decode('utf-8'))

        # Question CSV
        resp = self.client.get(reverse('portal:download_sample_question_csv'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertIn('question_text,option_a,option_b,option_c,option_d,correct_option', resp.content.decode('utf-8'))

    def test_state_preservation_on_back_navigation(self):
        """
        Verify that returning from Student History or Exam instructions
        preserves the selected class, student, and search filter parameters.
        """
        # 1. Student history back link preserves class_id and student_id
        hist_url = reverse('portal:student_history', args=[self.student.id])
        resp_hist = self.client.get(hist_url)
        self.assertEqual(resp_hist.status_code, 200)
        expected_back_param = f"class_id={self.academic_class.id}&student_id={self.student.id}"
        self.assertContains(resp_hist, expected_back_param)

        # 2. Exam instruction change student link preserves class_id, student_id, and exam_id
        inst_url = reverse('portal:exam_instruction', args=[self.exam.id])
        resp_inst = self.client.get(f"{inst_url}?student_id={self.student.id}")
        self.assertEqual(resp_inst.status_code, 200)
        self.assertContains(resp_inst, f"class_id={self.academic_class.id}&student_id={self.student.id}&exam_id={self.exam.id}")

        # 3. Index page renders preserved state variables
        index_url = f"{reverse('portal:index')}?class_id={self.academic_class.id}&student_id={self.student.id}&q=Rohan"
        resp_index = self.client.get(index_url)
        self.assertEqual(resp_index.status_code, 200)
        self.assertEqual(resp_index.context['selected_class'], self.academic_class)
        self.assertEqual(resp_index.context['selected_student_id'], str(self.student.id))
        self.assertEqual(resp_index.context['filter_query'], "Rohan")
        self.assertContains(resp_index, "clearFilterBtn")

    def test_student_exam_status_categorization(self):
        """
        Test that student's attempted vs pending exams are properly tracked and categorized.
        """
        # Create second exam (unattempted)
        exam2 = Exam.objects.create(
            title="Science Unit Test 2",
            subject="Science",
            duration_minutes=20,
            passing_percentage=Decimal('40.00')
        )
        exam2.classes.add(self.academic_class)

        # 1. Before attempting: API returns empty status map
        status_url = reverse('portal:get_student_exam_status', args=[self.student.id])
        resp = self.client.get(status_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status_map'], {})

        # 2. Complete an attempt for exam 1
        attempt = ExamAttempt.objects.create(
            exam=self.exam,
            student=self.student,
            attempt_number=1,
            total_questions=2,
            correct_answers=2,
            score_obtained=Decimal('4.00'),
            max_score=Decimal('4.00'),
            percentage=Decimal('100.00'),
            is_passed=True,
            is_completed=True
        )

        # 3. After attempting: API returns exam 1 as attempted
        resp = self.client.get(status_url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn(str(self.exam.id), data['status_map'])
        self.assertTrue(data['status_map'][str(self.exam.id)]['attempted'])
        self.assertEqual(data['status_map'][str(self.exam.id)]['count'], 1)
        self.assertEqual(data['status_map'][str(self.exam.id)]['best_score'], 4.0)

        # 4. Check class-data API with student_id param
        class_data_url = f"{reverse('portal:get_class_data', args=[self.academic_class.id])}?student_id={self.student.id}"
        resp_cd = self.client.get(class_data_url)
        self.assertEqual(resp_cd.status_code, 200)
        cd_data = resp_cd.json()
        self.assertTrue(cd_data['success'])
        
        # Verify exam 1 is marked as attempted, and exam 2 is not
        exam1_info = next(e for e in cd_data['exams'] if e['id'] == self.exam.id)
        exam2_info = next(e for e in cd_data['exams'] if e['id'] == exam2.id)
        self.assertTrue(exam1_info['is_attempted'])
        self.assertEqual(exam1_info['attempt_count'], 1)
        self.assertFalse(exam2_info['is_attempted'])
        self.assertEqual(exam2_info['attempt_count'], 0)

    def test_supervisor_student_single_delete(self):
        """Test supervisor can delete an individual student."""
        self.client.force_login(self.superuser)
        st = Student.objects.create(
            student_class=self.academic_class,
            name="Single Delete Student",
            roll_number="DEL-001"
        )
        delete_url = reverse('portal:supervisor_student_delete', args=[st.id])
        class_url = reverse('portal:supervisor_class_detail', args=[self.academic_class.id])

        # POST delete with next redirect
        response = self.client.post(delete_url, {'next': class_url})
        self.assertRedirects(response, class_url)
        self.assertFalse(Student.objects.filter(id=st.id).exists())

    def test_supervisor_students_bulk_delete(self):
        """Test supervisor can bulk-delete multiple selected students at once."""
        self.client.force_login(self.superuser)
        st1 = Student.objects.create(
            student_class=self.academic_class,
            name="Bulk Student 1",
            roll_number="BLK-001"
        )
        st2 = Student.objects.create(
            student_class=self.academic_class,
            name="Bulk Student 2",
            roll_number="BLK-002"
        )
        st3 = Student.objects.create(
            student_class=self.academic_class,
            name="Bulk Student 3",
            roll_number="BLK-003"
        )

        bulk_url = reverse('portal:supervisor_students_bulk_delete')
        class_url = reverse('portal:supervisor_class_detail', args=[self.academic_class.id])

        # Delete st1 and st2 via selected_student_ids list
        response = self.client.post(bulk_url, {
            'selected_student_ids': [st1.id, st2.id],
            'next': class_url
        })
        self.assertRedirects(response, class_url)
        self.assertFalse(Student.objects.filter(id=st1.id).exists())
        self.assertFalse(Student.objects.filter(id=st2.id).exists())
        self.assertTrue(Student.objects.filter(id=st3.id).exists())

        # Also test via student_ids_csv
        response2 = self.client.post(bulk_url, {
            'student_ids_csv': f"{st3.id}",
            'next': class_url
        })
        self.assertRedirects(response2, class_url)
        self.assertFalse(Student.objects.filter(id=st3.id).exists())

    def test_supervisor_reports_hub(self):
        """Test supervisor reports hub displays summary stats and classes/students."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_reports_hub')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/supervisor/reports_hub.html')
        self.assertIn('total_classes', response.context)
        self.assertIn('total_exams', response.context)
        self.assertContains(response, self.academic_class.name)
        self.assertContains(response, self.student.name)

    def test_supervisor_class_report_web(self):
        """Test class-wise web report renders with scheduled vs attempted metrics."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_class_report', args=[self.academic_class.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/supervisor/report_class_view.html')
        self.assertContains(response, self.academic_class.name)
        self.assertContains(response, self.exam.title)
        self.assertContains(response, "Mock Tests Schedule & Student Coverage")

    def test_supervisor_class_report_pdf(self):
        """Test class-wise PDF export generates valid A4 PDF binary stream."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_class_report_pdf', args=[self.academic_class.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn('attachment; filename="Class_Report_', response['Content-Disposition'])

    def test_supervisor_class_report_excel(self):
        """Test class-wise Excel export generates valid .xlsx spreadsheet."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_class_report_excel', args=[self.academic_class.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertTrue(len(response.content) > 1000)
        self.assertIn('attachment; filename="Class_Report_', response['Content-Disposition'])

    def test_supervisor_student_report_web(self):
        """Test student-wise web scorecard renders with attempt history and pending tests."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_student_report', args=[self.student.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'portal/supervisor/report_student_view.html')
        self.assertContains(response, self.student.name)
        self.assertContains(response, self.student.roll_number)
        self.assertContains(response, "OFFICIAL STUDENT EXAMINATION SCORECARD")

    def test_supervisor_student_report_pdf(self):
        """Test student-wise PDF scorecard generates valid A4 PDF binary stream."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_student_report_pdf', args=[self.student.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn('attachment; filename="Student_Report_', response['Content-Disposition'])

    def test_supervisor_student_report_excel(self):
        """Test student-wise Excel scorecard generates valid .xlsx spreadsheet."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_student_report_excel', args=[self.student.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertTrue(len(response.content) > 1000)
        self.assertIn('attachment; filename="Student_Report_', response['Content-Disposition'])

    def test_subject_model_and_academic_class_relation(self):
        """Test Subject model creation, representation, and class property."""
        subject = Subject.objects.create(
            academic_class=self.academic_class,
            name="Physics",
            code="PHY"
        )
        self.assertEqual(str(subject), "Physics (Class 10 - Science)")
        self.assertGreaterEqual(self.academic_class.total_subjects, 1)

    def test_api_class_data_includes_subjects(self):
        """Test get_class_data API returns subjects array with test metrics."""
        response = self.client.get(reverse('portal:get_class_data', args=[self.academic_class.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('subjects', data)
        subject_names = [s['name'] for s in data['subjects']]
        self.assertIn("Science", subject_names)

    def test_api_student_exam_status_with_subjects(self):
        """Test get_student_exam_status API returns subject-wise pending and completed stats."""
        math_exam = Exam.objects.create(
            title="Mathematics Algebra Test",
            subject="Mathematics",
            duration_minutes=20,
            passing_percentage=Decimal('40.00'),
            negative_marking=Decimal('0.00')
        )
        math_exam.classes.add(self.academic_class)

        # Complete an attempt on the Science exam
        ExamAttempt.objects.create(
            exam=self.exam,
            student=self.student,
            is_completed=True,
            max_score=Decimal('4.00'),
            score_obtained=Decimal('4.00'),
            percentage=Decimal('100.00'),
            is_passed=True
        )

        response = self.client.get(reverse('portal:get_student_exam_status', args=[self.student.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('subjects', data)
        sub_map = {s['name']: s for s in data['subjects']}
        self.assertIn('Science', sub_map)
        self.assertIn('Mathematics', sub_map)
        self.assertEqual(sub_map['Science']['attempted_exams'], 1)
        self.assertEqual(sub_map['Science']['pending_exams'], 0)
        self.assertEqual(sub_map['Mathematics']['attempted_exams'], 0)
        self.assertEqual(sub_map['Mathematics']['pending_exams'], 1)

    def test_supervisor_subject_create_and_delete(self):
        """Test supervisor can add and delete class subjects."""
        self.client.force_login(self.superuser)
        create_url = reverse('portal:supervisor_subject_create', args=[self.academic_class.id])
        response = self.client.post(create_url, {
            'name': 'Chemistry',
            'code': 'CHEM',
            'description': 'Chemistry for 10th'
        })
        self.assertEqual(response.status_code, 302)
        chem = Subject.objects.filter(academic_class=self.academic_class, name='Chemistry').first()
        self.assertIsNotNone(chem)

        delete_url = reverse('portal:supervisor_subject_delete', args=[chem.id])
        del_response = self.client.post(delete_url)
        self.assertEqual(del_response.status_code, 302)
        self.assertFalse(Subject.objects.filter(id=chem.id).exists())

    def test_supervisor_exam_create_auto_syncs_subject(self):
        """Test scheduling an exam with a subject auto-creates the Subject for assigned classes."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_exam_create')
        post_data = {
            'title': 'Biology Unit Test',
            'subject': 'Biology',
            'classes': [self.academic_class.id],
            'duration_minutes': 30,
            'passing_percentage': '50.00',
            'negative_marking': '0.00',
            'is_active': 'on'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        bio_sub = Subject.objects.filter(academic_class=self.academic_class, name='Biology').first()
        self.assertIsNotNone(bio_sub)

    def test_supervisor_exams_filter_by_class_and_subject(self):
        """Test mock tests listing can be filtered by class and subject."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_exams')
        response = self.client.get(f"{url}?class_id={self.academic_class.id}&subject=Science")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Science Unit Test 1")

    def test_supervisor_api_class_subjects_returns_database_subjects(self):
        """Test supervisor AJAX API returns subjects belonging to specified class from database."""
        self.client.force_login(self.superuser)
        Subject.objects.create(academic_class=self.academic_class, name='English Grammar')
        url = reverse('portal:supervisor_api_class_subjects')
        response = self.client.get(f"{url}?class_ids={self.academic_class.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn(str(self.academic_class.id), data['class_subjects'])
        subjects = data['class_subjects'][str(self.academic_class.id)]['subjects']
        self.assertIn('English Grammar', subjects)

    def test_supervisor_exam_create_get_contains_class_subjects_json(self):
        """Test supervisor exam create view passes dynamic class-to-subjects JSON to template."""
        self.client.force_login(self.superuser)
        Subject.objects.create(academic_class=self.academic_class, name='History & Civics')
        url = reverse('portal:supervisor_exam_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('class_subjects_json', response.context)
        self.assertContains(response, 'History & Civics')
        self.assertContains(response, 'dynamicSubjectSelect')

    def test_deleted_subject_never_reappears_on_public_portal(self):
        """Test that when a subject is deleted from a class, it never appears in the public portal API."""
        math_sub = Subject.objects.create(academic_class=self.academic_class, name='Mathematics')
        it_sub = Subject.objects.create(academic_class=self.academic_class, name='Information Technology')

        # Exam with IT subject
        it_exam = Exam.objects.create(
            title="IT Mock Test",
            subject="Information Technology",
            duration_minutes=30
        )
        it_exam.classes.add(self.academic_class)

        # Before deletion, both subjects appear in get_class_data
        res_before = self.client.get(reverse('portal:get_class_data', args=[self.academic_class.id]))
        subs_before = [s['name'] for s in res_before.json()['subjects']]
        self.assertIn('Mathematics', subs_before)
        self.assertIn('Information Technology', subs_before)

        # Supervisor deletes 'Information Technology'
        self.client.force_login(self.superuser)
        del_url = reverse('portal:supervisor_subject_delete', args=[it_sub.id])
        del_resp = self.client.post(del_url)
        self.assertEqual(del_resp.status_code, 302)

        # After deletion, 'Information Technology' MUST NOT appear in get_class_data
        res_after = self.client.get(reverse('portal:get_class_data', args=[self.academic_class.id]))
        subs_after = [s['name'] for s in res_after.json()['subjects']]
        self.assertIn('Mathematics', subs_after)
        self.assertNotIn('Information Technology', subs_after)

        # Also verify in student exam status API
        student_res = self.client.get(reverse('portal:get_student_exam_status', args=[self.student.id]))
        student_subs = [s['name'] for s in student_res.json()['subjects']]
        self.assertIn('Mathematics', student_subs)
        self.assertNotIn('Information Technology', student_subs)

        # Verify exam under that deleted subject had its subject detached
        it_exam.refresh_from_db()
        self.assertEqual(it_exam.subject, '')

    def test_format_questions_to_text(self):
        """Test serializing Question objects to Smart Parser text format."""
        formatted = format_questions_to_text([self.q1, self.q2])
        self.assertIn("1. What is the chemical formula of water?", formatted)
        self.assertIn("A) H2O", formatted)
        self.assertIn("Ans: A", formatted)
        self.assertIn("Explanation: Water is H2O.", formatted)
        self.assertIn("2. Which planet is the Red Planet?", formatted)
        self.assertIn("B) Mars", formatted)
        self.assertIn("Ans: B", formatted)

        # Roundtrip test
        parsed, errors = parse_bulk_question_text(formatted)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(len(errors), 0)
        self.assertEqual(parsed[0]['question_text'], "What is the chemical formula of water?")
        self.assertEqual(parsed[0]['correct_option'], "A")
        self.assertEqual(parsed[1]['question_text'], "Which planet is the Red Planet?")
        self.assertEqual(parsed[1]['correct_option'], "B")

    def test_supervisor_api_exam_questions(self):
        """Test supervisor AJAX API returns existing questions and count for an exam."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_api_exam_questions', args=[self.exam.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['exam_id'], self.exam.id)
        self.assertEqual(data['question_count'], 2)
        self.assertIn("What is the chemical formula of water?", data['raw_text'])
        self.assertIn("Which planet is the Red Planet?", data['raw_text'])

    def test_supervisor_bulk_questions_get_prepopulates_existing_questions(self):
        """Test bulk questions view pre-populates existing questions when exam_id is passed."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_exam_bulk_questions', args=[self.exam.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is the chemical formula of water?")
        self.assertContains(response, "Which planet is the Red Planet?")
        self.assertEqual(response.context['existing_count'], 2)

    def test_supervisor_bulk_questions_save_mode_replace(self):
        """Test save_text_questions with replace mode updates existing questions without duplicating."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_bulk_questions')
        
        updated_questions = [
            {
                'order': 1,
                'question_text': "What is the chemical formula of water? (Updated Statement)",
                'option_a': "H2O",
                'option_b': "CO2",
                'option_c': "NaCl",
                'option_d': "CH4",
                'correct_option': "A",
                'marks': "2.0",
                'negative_marks': "0.5",
                'explanation': "Updated explanation.",
            },
            {
                'order': 2,
                'question_text': "Which planet is closest to the Sun?",
                'option_a': "Mercury",
                'option_b': "Venus",
                'option_c': "Earth",
                'option_d': "Mars",
                'correct_option': "A",
                'marks': "2.0",
                'negative_marks': "0.5",
                'explanation': "Mercury is closest.",
            }
        ]

        post_data = {
            'action_type': 'save_text_questions',
            'target_exam_id': self.exam.id,
            'questions_json': json.dumps(updated_questions),
            'save_mode': 'replace',
        }
        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse('portal:supervisor_exam_detail', args=[self.exam.id]))

        # Count must remain 2 (not 4)
        self.assertEqual(self.exam.questions.count(), 2)
        q1_refreshed = Question.objects.get(id=self.q1.id)
        self.assertEqual(q1_refreshed.question_text, "What is the chemical formula of water? (Updated Statement)")
        self.assertEqual(q1_refreshed.explanation, "Updated explanation.")

        q2_refreshed = Question.objects.get(id=self.q2.id)
        self.assertEqual(q2_refreshed.question_text, "Which planet is closest to the Sun?")
        self.assertEqual(q2_refreshed.correct_option, "A")

    def test_supervisor_bulk_questions_save_mode_append(self):
        """Test save_text_questions with append mode appends new questions to existing ones."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_bulk_questions')

        new_question = [
            {
                'order': 1,
                'question_text': "What is the powerhouse of the cell?",
                'option_a': "Nucleus",
                'option_b': "Ribosome",
                'option_c': "Mitochondria",
                'option_d': "ER",
                'correct_option': "C",
                'marks': "1.0",
                'negative_marks': "0.0",
                'explanation': "Mitochondria.",
            }
        ]

        post_data = {
            'action_type': 'save_text_questions',
            'target_exam_id': self.exam.id,
            'questions_json': json.dumps(new_question),
            'save_mode': 'append',
        }
        response = self.client.post(url, post_data)
        self.assertRedirects(response, reverse('portal:supervisor_exam_detail', args=[self.exam.id]))

        # Count must increase from 2 to 3
        self.assertEqual(self.exam.questions.count(), 3)

    def test_supervisor_mobile_navigation_elements(self):
        """Test supervisor layout renders mobile navigation collapse controls and backdrop overlay."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="sidebarCloseBtn"')
        self.assertContains(response, 'id="sidebarBackdrop"')
        self.assertContains(response, 'id="sidebarToggleBtn"')
        self.assertContains(response, 'sidebar-header')

    def test_exam_attempt_result_pdf_download_and_content(self):
        """
        Verify that attempting an exam and clicking Download PDF Report produces
        a valid, non-blank server-side PDF with complete scorecard, questions, options,
        and official school branding.
        """
        import io
        import pypdf

        # 1. Create a completed exam attempt with answers
        attempt = ExamAttempt.objects.create(
            exam=self.exam,
            student=self.student,
            attempt_number=1,
            completed_at=timezone.now(),
            total_questions=2,
            correct_answers=1,
            wrong_answers=1,
            unattempted_answers=0,
            score_obtained=Decimal('1.50'),
            max_score=Decimal('4.00'),
            percentage=Decimal('37.50'),
            is_passed=False,
            is_completed=True,
            time_taken_seconds=95
        )
        AttemptAnswer.objects.create(
            attempt=attempt,
            question=self.q1,
            selected_option='A',
            is_correct=True,
            marks_awarded=Decimal('2.00')
        )
        AttemptAnswer.objects.create(
            attempt=attempt,
            question=self.q2,
            selected_option='C',
            is_correct=False,
            marks_awarded=Decimal('-0.50')
        )

        # 2. Request PDF download endpoint
        pdf_url = reverse('portal:attempt_result_pdf', args=[attempt.id])
        response = self.client.get(pdf_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('.pdf', response['Content-Disposition'])
        self.assertGreater(len(response.content), 20000, "PDF byte length must be substantial (not empty/blank)")

        # 3. Parse PDF with pypdf and verify text content across pages
        reader = pypdf.PdfReader(io.BytesIO(response.content))
        self.assertGreaterEqual(len(reader.pages), 1)

        full_extracted_text = ""
        for page in reader.pages:
            full_extracted_text += page.extract_text() or ""

        # Verify school branding
        self.assertIn("Arohan Academy English School", full_extracted_text)
        # Verify student & exam info
        self.assertIn("Rohan Sharma", full_extracted_text)
        self.assertIn("Science Unit Test 1", full_extracted_text)
        self.assertIn("ARO-001", full_extracted_text)
        # Verify scorecard details
        self.assertIn("1.50 / 4.00", full_extracted_text)
        self.assertIn("37.50%", full_extracted_text)
        self.assertIn("FAILED", full_extracted_text)
        # Verify questions and options
        self.assertIn("What is the chemical formula of water?", full_extracted_text)
        self.assertIn("H2O", full_extracted_text)
        self.assertIn("Which planet is the Red Planet?", full_extracted_text)
        self.assertIn("Mars", full_extracted_text)

    def test_exam_result_view_has_server_side_pdf_download_links(self):
        """
        Verify that the student exam result page links directly to the server-side PDF generator
        and avoids brittle html2pdf client-side canvas capture.
        """
        attempt = ExamAttempt.objects.create(
            exam=self.exam,
            student=self.student,
            attempt_number=1,
            total_questions=2,
            correct_answers=2,
            wrong_answers=0,
            unattempted_answers=0,
            score_obtained=Decimal('4.00'),
            max_score=Decimal('4.00'),
            percentage=Decimal('100.00'),
            is_passed=True,
            is_completed=True,
            time_taken_seconds=60
        )
        url = reverse('portal:exam_result', args=[attempt.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        expected_pdf_url = reverse('portal:attempt_result_pdf', args=[attempt.id])
        self.assertContains(response, f'href="{expected_pdf_url}"')
        self.assertContains(response, 'Download PDF Report')
        self.assertNotContains(response, 'html2pdf.bundle.min.js')

    def test_confirm_delete_with_raw_cancel_url(self):
        """Verify confirm_delete template supports raw URL path in cancel_url without NoReverseMatch."""
        self.client.force_login(self.superuser)
        url = reverse('portal:supervisor_student_delete', args=[self.student.id]) + '?next=/supervisor/classes/1/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/supervisor/classes/1/"')

    def test_exam_submit_records_accurate_started_at(self):
        """Verify that ExamAttempt.started_at is calculated from completed_at minus time_taken_seconds."""
        submit_url = reverse('portal:exam_submit', args=[self.exam.id])
        post_data = {
            'student_id': self.student.id,
            'time_taken_seconds': 300,
            f'question_{self.q1.id}': 'A',
            f'question_{self.q2.id}': 'B',
        }
        response = self.client.post(submit_url, post_data)
        self.assertEqual(response.status_code, 302)

        attempt = ExamAttempt.objects.filter(student=self.student, exam=self.exam).last()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.time_taken_seconds, 300)
        diff_seconds = (attempt.completed_at - attempt.started_at).total_seconds()
        self.assertAlmostEqual(diff_seconds, 300, delta=2)
