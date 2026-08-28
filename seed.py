"""Populate the database with a small demo dataset.

Run with:  flask seed-db   (after  flask init-db)
"""
from datetime import date, time, timedelta

from app import app
from extensions import db
from models import (
    User, Student, Teacher, Course, Department, ClassGroup, Subject,
    Attendance, Mark, Fee, Notice, StudyMaterial, Timetable, Event,
    Book, BookIssue, Bus, Exam, Employee, Laboratory, DepartmentAchievement,
    PlacementRecord, DepartmentDocument,
)
from utils import generate_code


def run_seed():
    with app.app_context():
        db.create_all()

        if User.query.filter_by(username="admin").first():
            print("Demo data already present, skipping seed.")
            return

        # --- Admin -----------------------------------------------------
        admin = User(full_name="System Admin", username="admin", email="admin@sms.local", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

        # --- Courses -----------------------------------------------------
        be = Course(name="B.E. / B.Tech", level="UG", duration_years=4, fee_amount=120000, has_departments=True)
        mba = Course(name="MBA", level="PG", duration_years=2, fee_amount=90000, has_departments=False)
        mca = Course(name="MCA", level="PG", duration_years=2, fee_amount=85000, has_departments=False)
        db.session.add_all([be, mba, mca])
        db.session.flush()

        # --- Departments (only under B.E./B.Tech) -------------------------
        cse = Department(
            name="Computer Science Engineering", course_id=be.id, fee_amount=15000,
            code="CSE", established_year=2005,
            vision="To be a center of excellence in computing education and research.",
            mission="Produce industry-ready engineers through strong fundamentals and innovation.",
            about="The CSE department offers a comprehensive undergraduate program covering software "
                  "engineering, AI/ML, and systems.",
            objectives="Foster problem-solving skills, ethical practice, and lifelong learning.",
            num_labs=1, growth_timeline="Started with 60 seats in 2005, expanded to 180 seats by 2020.",
            achievements_summary="Multiple university rank holders; strong placement record.",
            accreditation_details="NBA Accredited (2021-2024)",
            university_affiliation="Visvesvaraya Technological University",
            milestones="2010: First PG program launched. 2018: New AI lab established.",
            highest_package=1800000, average_package=650000,
            recruiters="Infosys\nTCS\nAmazon\nMicrosoft",
            contact_email="cse@college.edu", contact_phone="080-12345678",
            contact_address="CSE Block, Main Campus", office_hours="Mon-Fri, 9:00 AM - 5:00 PM",
        )
        ece = Department(name="Electronics & Communication", course_id=be.id, fee_amount=14000)
        db.session.add_all([cse, ece])
        db.session.flush()

        # --- Class / section ------------------------------------------
        cse_sem3 = ClassGroup(department_id=cse.id, semester=3, section="A")
        db.session.add(cse_sem3)
        db.session.flush()

        # --- Teacher (also the CSE HOD) -----------------------------------------------------
        t_user = User(full_name="Dr. Anita Rao", username="anita.rao", email="anita.rao@sms.local", role="teacher")
        t_user.set_password("teacher123")
        db.session.add(t_user)
        db.session.flush()

        teacher = Teacher(
            user_id=t_user.id, qualification="Ph.D Computer Science",
            department_id=cse.id, designation="HOD", experience_years=12,
            cabin_number="CSE-201", office_hours="Mon/Wed 2-4 PM",
            research_areas="Machine Learning, Distributed Systems",
            publications="12 papers in IEEE/ACM conferences",
            certifications="AWS Certified Solutions Architect",
            projects="Smart Campus IoT Platform", awards="Best Teacher Award 2022",
        )
        db.session.add(teacher)
        db.session.flush()
        teacher.teacher_code = generate_code("TCH", teacher.id)

        cse.hod_teacher_id = teacher.id
        cse.hod_cabin_number = "CSE-201"
        cse.hod_message = "Welcome to the Department of Computer Science Engineering! We are committed to nurturing innovative, ethical, and industry-ready engineers."

        # --- Subjects -----------------------------------------------------
        dsa = Subject(name="Data Structures", code="CS301", department_id=cse.id, semester=3, credit_hours=4, teacher_id=teacher.id)
        dbms = Subject(name="Database Management Systems", code="CS302", department_id=cse.id, semester=3, credit_hours=4, teacher_id=teacher.id)
        db.session.add_all([dsa, dbms])
        db.session.flush()

        # --- Student -----------------------------------------------------
        s_user = User(
            full_name="Rahul Sharma", username="rahul.sharma", email="rahul.sharma@sms.local",
            phone="9876543210", gender="Male", role="student",
        )
        s_user.set_password("student123")
        db.session.add(s_user)
        db.session.flush()

        student = Student(
            user_id=s_user.id, blood_group="O+", address="12 MG Road, Bengaluru",
            parent_name="Suresh Sharma", parent_phone="9998887770",
            course_id=be.id, department_id=cse.id, class_group_id=cse_sem3.id,
            semester=3, admission_date=date.today() - timedelta(days=200), status="Active",
            bus_number="12", bus_route="City Center - Campus",
        )
        db.session.add(student)
        db.session.flush()
        student.student_code = generate_code("STU", student.id)

        # --- Attendance -----------------------------------------------------
        for i in range(10):
            db.session.add(Attendance(
                student_id=student.id, subject_id=dsa.id,
                date=date.today() - timedelta(days=i),
                status="Present" if i % 4 else "Absent",
                marked_by=teacher.id,
            ))

        # --- Marks -----------------------------------------------------
        db.session.add(Mark(student_id=student.id, subject_id=dsa.id, internal_marks=28, external_marks=58))
        db.session.add(Mark(student_id=student.id, subject_id=dbms.id, internal_marks=25, external_marks=50))

        # --- Fees -----------------------------------------------------
        db.session.add(Fee(student_id=student.id, fee_name="College Fee", amount=135000, paid_amount=135000))
        db.session.add(Fee(student_id=student.id, fee_name="Exam Fee", amount=2000, paid_amount=0))

        # --- Notice -----------------------------------------------------
        db.session.add(Notice(title="Welcome to the new semester!", content="Classes begin Monday. Please check your timetable.", posted_by=admin.id))

        # --- Study material -----------------------------------------------------
        db.session.add(StudyMaterial(title="Unit 1 Notes", subject_id=dsa.id, teacher_id=teacher.id))

        # --- Timetable -----------------------------------------------------
        db.session.add(Timetable(department_id=cse.id, day_of_week="Monday", period=1, subject_id=dsa.id,
                                  start_time=time(9, 0), end_time=time(10, 0)))
        db.session.add(Timetable(department_id=cse.id, day_of_week="Monday", period=2, subject_id=dbms.id,
                                  start_time=time(10, 0), end_time=time(11, 0)))

        # --- Events -----------------------------------------------------
        db.session.add(Event(title="Annual Tech Fest", category="College Event",
                              event_date=date.today() + timedelta(days=20), location="Main Auditorium"))
        db.session.add(Event(title="Python Workshop", category="Workshop",
                              event_date=date.today() + timedelta(days=7), location="Lab 2"))

        # --- Library -----------------------------------------------------
        book = Book(title="Introduction to Algorithms", author="Cormen et al.", isbn="9780262033848",
                    total_copies=3, available_copies=2)
        db.session.add(book)
        db.session.flush()
        db.session.add(BookIssue(book_id=book.id, student_id=student.id,
                                  issue_date=date.today() - timedelta(days=5),
                                  due_date=date.today() + timedelta(days=9)))

        # --- Transport -----------------------------------------------------
        db.session.add(Bus(bus_number="12", route="City Center - Campus",
                            driver_name="Manoj Kumar", driver_phone="9123456780"))

        # --- Exam -----------------------------------------------------
        db.session.add(Exam(name="Mid-Semester Exam", course_id=be.id, subject_id=dsa.id,
                             exam_hall="Hall A", exam_date=date.today() + timedelta(days=14),
                             exam_time=time(10, 0)))

        # --- Employees (HR module) -----------------------------------------------------
        acc_user = User(full_name="Kavita Nair", username="kavita.nair", email="kavita.nair@sms.local", role="employee")
        acc_user.set_password("employee123")
        db.session.add(acc_user)
        db.session.flush()
        accountant = Employee(
            user_id=acc_user.id, department_id=None, designation="Accountant",
            qualification="M.Com", experience_years=6, joining_date=date.today() - timedelta(days=400),
            salary=42000, employment_type="Permanent", status="Active",
        )
        db.session.add(accountant)
        db.session.flush()
        accountant.employee_code = generate_code("EMP", accountant.id)

        lib_user = User(full_name="Ramesh Gupta", username="ramesh.gupta", email="ramesh.gupta@sms.local", role="employee")
        lib_user.set_password("employee123")
        db.session.add(lib_user)
        db.session.flush()
        librarian = Employee(
            user_id=lib_user.id, department_id=cse.id, designation="Librarian",
            qualification="B.Lib", experience_years=4, joining_date=date.today() - timedelta(days=200),
            salary=28000, employment_type="Permanent", status="Active",
        )
        db.session.add(librarian)
        db.session.flush()
        librarian.employee_code = generate_code("EMP", librarian.id)

        # --- Department microsite extras (CSE) -----------------------------------------------------
        db.session.add(Laboratory(
            department_id=cse.id, name="AI & Machine Learning Lab", incharge_teacher_id=teacher.id,
            num_systems=30, software_installed="Python, TensorFlow, PyTorch, MATLAB",
            equipment_list="30 workstations, 2 GPU servers, network switches",
            timetable_note="Available Mon-Fri, 9 AM - 5 PM",
        ))
        db.session.add(DepartmentAchievement(
            department_id=cse.id, title="Best Paper Award — IEEE Conference", category="Research Publication",
            description="Awarded for research on distributed ML systems.", achieved_on=date.today() - timedelta(days=60),
        ))
        db.session.add(PlacementRecord(
            department_id=cse.id, student_id=student.id, company="Amazon", package=1800000,
            year=date.today().year, notes="Software Development Engineer",
        ))
        db.session.add(Event(
            title="AI Hackathon", category="Hackathon", department_id=cse.id,
            event_date=date.today() + timedelta(days=10), location="CSE Seminar Hall",
        ))
        db.session.add(Notice(
            title="CSE Mid-Sem Exam Schedule", content="Mid-semester exams start next Monday.",
            posted_by=admin.id, department_id=cse.id,
        ))
        db.session.add(DepartmentDocument(
            department_id=cse.id, category="Academic Calendar", title="2026 Academic Calendar",
        ))

        db.session.commit()
        print("Seed complete. Login as admin/admin123, anita.rao/teacher123, rahul.sharma/student123, kavita.nair/employee123")


if __name__ == "__main__":
    run_seed()
