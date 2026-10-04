from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from portal.models import AcademicClass, Student, Exam, Question, ExamAttempt, AttemptAnswer


class Command(BaseCommand):
    help = "Seeds initial sample data for Arohan Academy Mocktest Portal"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Arohan Academy Mocktest Portal data...")

        # 1. Superuser
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@arohanacademy.com', 'admin123')
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' created with password 'admin123'."))

        # 2. Classes
        c10, _ = AcademicClass.objects.get_or_create(
            name="Class 10 - Science & Mathematics",
            defaults={"code": "C10-SM", "description": "Secondary Board Foundation Batch for Class 10."}
        )
        c12, _ = AcademicClass.objects.get_or_create(
            name="Class 12 - Physics & Chemistry",
            defaults={"code": "C12-PC", "description": "Senior Secondary Board & Competitive Foundation."}
        )
        fnd, _ = AcademicClass.objects.get_or_create(
            name="Foundation Batch - General Aptitude",
            defaults={"code": "FND-GA", "description": "General Aptitude and Reasoning Batch."}
        )

        self.stdout.write(self.style.SUCCESS("Classes created."))

        # 3. Students
        students_data = [
            # Class 10
            (c10, "ARO-101", "Aarav Sharma", "9876543210", "aarav@example.com"),
            (c10, "ARO-102", "Priya Patel", "9876543211", "priya@example.com"),
            (c10, "ARO-103", "Rohan Verma", "9876543212", "rohan@example.com"),
            (c10, "ARO-104", "Ananya Gupta", "9876543213", "ananya@example.com"),
            (c10, "ARO-105", "Kabir Singh", "9876543214", "kabir@example.com"),
            # Class 12
            (c12, "ARO-201", "Diya Mukherjee", "9876543220", "diya@example.com"),
            (c12, "ARO-202", "Arjun Nair", "9876543221", "arjun@example.com"),
            (c12, "ARO-203", "Sneha Rao", "9876543222", "sneha@example.com"),
            (c12, "ARO-204", "Vikram Malhotra", "9876543223", "vikram@example.com"),
            # Foundation
            (fnd, "ARO-301", "Aditi Kulkarni", "9876543230", "aditi@example.com"),
            (fnd, "ARO-302", "Rishi Kapoor", "9876543231", "rishi@example.com"),
            (fnd, "ARO-303", "Meera Joshi", "9876543232", "meera@example.com"),
        ]

        created_students = {}
        for c, roll, name, phone, email in students_data:
            s, _ = Student.objects.update_or_create(
                student_class=c,
                roll_number=roll,
                defaults={"name": name, "phone": phone, "email": email, "is_active": True}
            )
            created_students[roll] = s

        self.stdout.write(self.style.SUCCESS(f"Students populated ({len(created_students)} total)."))

        # 4. Exam 1: Class 10 Science
        exam1, _ = Exam.objects.get_or_create(
            title="Class 10 Science: Chemical Reactions & Acids",
            defaults={
                "code": "MT-C10-SCI-01",
                "subject": "Science",
                "description": "Comprehensive mock test covering Chemical Equations, Balancing, Oxidation, and pH scale.",
                "duration_minutes": 15,
                "passing_percentage": Decimal("40.00"),
                "negative_marking": Decimal("0.25"),
                "shuffle_questions": False,
                "is_active": True,
            }
        )
        exam1.classes.set([c10])

        q1_data = [
            (
                1,
                "Which of the following is a displacement reaction?",
                "MgCO3 → MgO + CO2",
                "2Na + 2H2O → 2NaOH + H2",
                "2H2 + O2 → 2H2O",
                "2Pb(NO3)2 → 2PbO + 4NO2 + O2",
                "B",
                Decimal("2.00"),
                Decimal("0.50"),
                "In 2Na + 2H2O → 2NaOH + H2, Sodium displaces hydrogen from water because sodium is more reactive than hydrogen."
            ),
            (
                2,
                "What is the pH value of pure distilled water at 25°C?",
                "pH = 0",
                "pH = 5",
                "pH = 7",
                "pH = 14",
                "C",
                Decimal("2.00"),
                Decimal("0.50"),
                "Pure water is neutral having equal concentrations of H+ and OH- ions, corresponding to a pH of 7 at 25°C."
            ),
            (
                3,
                "Rusting of iron is an example of which type of chemical process?",
                "Decomposition only",
                "Reduction only",
                "Redox reaction and Oxidation",
                "Endothermic neutralization",
                "C",
                Decimal("2.00"),
                Decimal("0.50"),
                "Rusting of iron is an oxidation-reduction (redox) reaction where iron reacts with oxygen and moisture to form hydrated ferric oxide."
            ),
            (
                4,
                "What gas is liberated when an active metal reacts with dilute hydrochloric acid?",
                "Carbon Dioxide (CO2)",
                "Hydrogen (H2)",
                "Nitrogen (N2)",
                "Chlorine (Cl2)",
                "B",
                Decimal("2.00"),
                Decimal("0.50"),
                "Metals react with dilute acids like HCl to produce metal salt and liberate Hydrogen gas (H2), which burns with a pop sound."
            ),
            (
                5,
                "Which substance is commonly used to treat acidity in the stomach (Antacid)?",
                "Sodium Hydroxide (NaOH)",
                "Magnesium Hydroxide [Milk of Magnesia]",
                "Hydrochloric acid (HCl)",
                "Copper Sulfate (CuSO4)",
                "B",
                Decimal("2.00"),
                Decimal("0.50"),
                "Magnesium Hydroxide [Mg(OH)2], also known as Milk of Magnesia, is a mild base safely used as an antacid to neutralize excess stomach acid."
            ),
        ]

        for order, q_text, opt_a, opt_b, opt_c, opt_d, correct, marks, neg_m, explanation in q1_data:
            Question.objects.update_or_create(
                exam=exam1,
                order=order,
                defaults={
                    "question_text": q_text,
                    "option_a": opt_a,
                    "option_b": opt_b,
                    "option_c": opt_c,
                    "option_d": opt_d,
                    "correct_option": correct,
                    "marks": marks,
                    "negative_marks": neg_m,
                    "explanation": explanation,
                }
            )

        # 5. Exam 2: Class 12 Physics
        exam2, _ = Exam.objects.get_or_create(
            title="Class 12 Physics: Electrostatics & Current Electricity",
            defaults={
                "code": "MT-C12-PHY-01",
                "subject": "Physics",
                "description": "Mock test on Coulomb's law, Electric Potential, Capacitance, and Ohm's law.",
                "duration_minutes": 20,
                "passing_percentage": Decimal("50.00"),
                "negative_marking": Decimal("0.25"),
                "shuffle_questions": False,
                "is_active": True,
            }
        )
        exam2.classes.set([c12])

        q2_data = [
            (
                1,
                "The SI unit of electric capacitance is:",
                "Farad (F)",
                "Henry (H)",
                "Tesla (T)",
                "Coulomb (C)",
                "A",
                Decimal("2.00"),
                Decimal("0.50"),
                "The SI unit of capacitance is the Farad (F), named after Michael Faraday. 1 Farad = 1 Coulomb / Volt."
            ),
            (
                2,
                "If the distance between two point charges is halved, the electrostatic force between them:",
                "Is halved",
                "Is doubled",
                "Becomes four times greater",
                "Remains unchanged",
                "C",
                Decimal("2.00"),
                Decimal("0.50"),
                "According to Coulomb's Law, Force is inversely proportional to the square of distance (F ∝ 1/r^2). Halving r multiplies F by (1 / 0.5^2) = 4."
            ),
            (
                3,
                "What is the electric field inside a charged hollow spherical conductor?",
                "Maximum at center",
                "Infinite",
                "Zero",
                "Proportional to radius",
                "C",
                Decimal("2.00"),
                Decimal("0.50"),
                "By Gauss's Law, the enclosed charge inside a hollow spherical conductor is zero, hence the electrostatic field inside is always zero."
            ),
            (
                4,
                "Kirchhoff's First Rule (Junction rule) is based on the conservation of:",
                "Energy",
                "Electric Charge",
                "Linear Momentum",
                "Mass",
                "B",
                Decimal("2.00"),
                Decimal("0.50"),
                "Kirchhoff's junction law states that total incoming current equals total outgoing current, which is based on conservation of electric charge."
            ),
        ]

        for order, q_text, opt_a, opt_b, opt_c, opt_d, correct, marks, neg_m, explanation in q2_data:
            Question.objects.update_or_create(
                exam=exam2,
                order=order,
                defaults={
                    "question_text": q_text,
                    "option_a": opt_a,
                    "option_b": opt_b,
                    "option_c": opt_c,
                    "option_d": opt_d,
                    "correct_option": correct,
                    "marks": marks,
                    "negative_marks": neg_m,
                    "explanation": explanation,
                }
            )

        # 6. Exam 3: General Mock Test (Assigned to all classes)
        exam3, _ = Exam.objects.get_or_create(
            title="General Aptitude & Logical Reasoning Mock Test 1",
            defaults={
                "code": "MT-GEN-01",
                "subject": "General Aptitude",
                "description": "Essential logical reasoning, numerical ability, and scientific fundamentals.",
                "duration_minutes": 10,
                "passing_percentage": Decimal("40.00"),
                "negative_marking": Decimal("0.00"),
                "shuffle_questions": False,
                "is_active": True,
            }
        )
        exam3.classes.set([c10, c12, fnd])

        q3_data = [
            (
                1,
                "Which number completes the sequence: 2, 6, 12, 20, 30, ?",
                "36",
                "40",
                "42",
                "48",
                "C",
                Decimal("2.00"),
                Decimal("0.00"),
                "The differences between consecutive numbers are +4, +6, +8, +10. Next difference is +12, so 30 + 12 = 42."
            ),
            (
                2,
                "If 'ROSE' is coded as '6821' and 'CHAIR' is coded as '73456', what is the code for 'SEARCH'?",
                "214673",
                "214763",
                "124673",
                "216473",
                "A",
                Decimal("2.00"),
                Decimal("0.00"),
                "Mapping letters: S=2, E=1, A=4, R=6, C=7, H=3. Hence SEARCH is 214673."
            ),
            (
                3,
                "A car travels 180 km in 3 hours. What is its speed in meters per second (m/s)?",
                "60 m/s",
                "16.67 m/s",
                "25 m/s",
                "30 m/s",
                "B",
                Decimal("2.00"),
                Decimal("0.00"),
                "Speed in km/h = 180 / 3 = 60 km/h. To convert to m/s, multiply by 5/18: 60 * (5/18) = 16.67 m/s."
            ),
        ]

        for order, q_text, opt_a, opt_b, opt_c, opt_d, correct, marks, neg_m, explanation in q3_data:
            Question.objects.update_or_create(
                exam=exam3,
                order=order,
                defaults={
                    "question_text": q_text,
                    "option_a": opt_a,
                    "option_b": opt_b,
                    "option_c": opt_c,
                    "option_d": opt_d,
                    "correct_option": correct,
                    "marks": marks,
                    "negative_marks": neg_m,
                    "explanation": explanation,
                }
            )

        # 7. Create sample completed attempt for Aarav Sharma (ARO-101) to verify reporting
        student_aarav = created_students["ARO-101"]
        if not ExamAttempt.objects.filter(student=student_aarav, exam=exam1).exists():
            attempt = ExamAttempt.objects.create(
                exam=exam1,
                student=student_aarav,
                attempt_number=1,
                started_at=timezone.now() - timezone.timedelta(hours=2),
                completed_at=timezone.now() - timezone.timedelta(hours=2) + timezone.timedelta(minutes=8, seconds=35),
                time_taken_seconds=515,
                total_questions=5,
                correct_answers=4,
                wrong_answers=1,
                unattempted_answers=0,
                score_obtained=Decimal("7.50"),
                max_score=Decimal("10.00"),
                percentage=Decimal("75.00"),
                is_passed=True,
                is_completed=True,
            )
            
            # Answers: Q1 correct (B), Q2 correct (C), Q3 correct (C), Q4 incorrect (A instead of B), Q5 correct (B)
            q_list = list(exam1.questions.order_by('order'))
            answers = [
                ('B', True, Decimal("2.00")),
                ('C', True, Decimal("2.00")),
                ('C', True, Decimal("2.00")),
                ('A', False, Decimal("-0.50")),
                ('B', True, Decimal("2.00")),
            ]
            for q, (ans_opt, is_corr, marks_aw) in zip(q_list, answers):
                AttemptAnswer.objects.create(
                    attempt=attempt,
                    question=q,
                    selected_option=ans_opt,
                    is_correct=is_corr,
                    marks_awarded=marks_aw
                )
            self.stdout.write(self.style.SUCCESS("Sample completed attempt created for Aarav Sharma."))

        self.stdout.write(self.style.SUCCESS("All seed data successfully loaded into Arohan Academy Mocktest Portal!"))
