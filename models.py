from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

# ---------------------------------------------------------------------------
# Core auth / user
# ---------------------------------------------------------------------------


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    dob = db.Column(db.Date)
    gender = db.Column(db.String(20))
    photo = db.Column(db.String(255))  # relative path under static/uploads
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # admin/teacher/student
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_profile = db.relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    teacher_profile = db.relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ---------------------------------------------------------------------------
# Academic structure
# ---------------------------------------------------------------------------


class Course(db.Model):
    """Top level program: e.g. B.E./B.Tech (UG) or MBA/MCA (PG)."""

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g. B.E./B.Tech, MBA, MCA
    level = db.Column(db.String(20), nullable=False)  # 'UG' or 'PG'
    duration_years = db.Column(db.Integer, default=4)
    fee_amount = db.Column(db.Numeric(10, 2), default=0)
    has_departments = db.Column(db.Boolean, default=True)  # PG courses like MBA/MCA => False

    departments = db.relationship("Department", back_populates="course", cascade="all, delete-orphan")
    students = db.relationship("Student", back_populates="course")


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g. CSE, ECE, Mechanical
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    fee_amount = db.Column(db.Numeric(10, 2), default=0)

    # --- Overview ---
    code = db.Column(db.String(20))
    established_year = db.Column(db.Integer)
    vision = db.Column(db.Text)
    mission = db.Column(db.Text)
    about = db.Column(db.Text)
    objectives = db.Column(db.Text)
    num_labs = db.Column(db.Integer, default=0)

    # --- History ---
    growth_timeline = db.Column(db.Text)
    achievements_summary = db.Column(db.Text)
    accreditation_details = db.Column(db.Text)
    university_affiliation = db.Column(db.String(200))
    milestones = db.Column(db.Text)

    # --- HOD ---
    hod_teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    hod_cabin_number = db.Column(db.String(30))
    hod_message = db.Column(db.Text)

    # --- Placements (summary stats; individual records in PlacementRecord) ---
    highest_package = db.Column(db.Numeric(10, 2))
    average_package = db.Column(db.Numeric(10, 2))
    recruiters = db.Column(db.Text)  # newline-separated company names

    # --- Contact ---
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    contact_address = db.Column(db.String(255))
    office_hours = db.Column(db.String(120))
    map_embed_url = db.Column(db.String(500))

    course = db.relationship("Course", back_populates="departments")
    students = db.relationship("Student", back_populates="department", foreign_keys="Student.department_id")
    subjects = db.relationship("Subject", back_populates="department", cascade="all, delete-orphan")
    hod_teacher = db.relationship("Teacher", foreign_keys=[hod_teacher_id])
    labs = db.relationship("Laboratory", back_populates="department", cascade="all, delete-orphan")
    dept_achievements = db.relationship("DepartmentAchievement", back_populates="department", cascade="all, delete-orphan")
    placement_records = db.relationship("PlacementRecord", back_populates="department", cascade="all, delete-orphan")
    documents = db.relationship("DepartmentDocument", back_populates="department", cascade="all, delete-orphan")
    contact_messages = db.relationship("DepartmentContactMessage", back_populates="department", cascade="all, delete-orphan")


class ClassGroup(db.Model):
    """A section/class, e.g. CSE - Sem 3 - Section A."""

    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    section = db.Column(db.String(10), default="A")

    department = db.relationship("Department")
    students = db.relationship("Student", back_populates="class_group")


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    semester = db.Column(db.Integer)
    credit_hours = db.Column(db.Integer, default=3)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    syllabus_file = db.Column(db.String(255))
    outcomes = db.Column(db.Text)

    department = db.relationship("Department", back_populates="subjects")
    teacher = db.relationship("Teacher", back_populates="subjects")


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    student_code = db.Column(db.String(30), unique=True)  # e.g. Student ID
    blood_group = db.Column(db.String(5))
    address = db.Column(db.String(255))
    parent_name = db.Column(db.String(120))
    parent_phone = db.Column(db.String(20))
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    class_group_id = db.Column(db.Integer, db.ForeignKey("classes.id"))
    semester = db.Column(db.Integer)
    admission_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(15), default="Active")  # Active/Inactive
    bus_number = db.Column(db.String(20))
    bus_route = db.Column(db.String(120))

    user = db.relationship("User", back_populates="student_profile")
    course = db.relationship("Course", back_populates="students")
    department = db.relationship("Department", back_populates="students")
    class_group = db.relationship("ClassGroup", back_populates="students")

    attendance_records = db.relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    submissions = db.relationship("AssignmentSubmission", back_populates="student", cascade="all, delete-orphan")
    marks = db.relationship("Mark", back_populates="student", cascade="all, delete-orphan")
    fees = db.relationship("Fee", back_populates="student", cascade="all, delete-orphan")
    leave_requests = db.relationship("LeaveRequest", back_populates="student", cascade="all, delete-orphan")


TEACHER_DESIGNATIONS = [
    "HOD", "Professor", "Associate Professor", "Assistant Professor",
    "Lab Instructor", "Non-Tech Professor", "Others",
]


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    teacher_code = db.Column(db.String(30), unique=True)
    qualification = db.Column(db.String(120))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    designation = db.Column(db.String(50))  # one of TEACHER_DESIGNATIONS
    experience_years = db.Column(db.Integer, default=0)
    cabin_number = db.Column(db.String(30))

    # --- Faculty profile (for the Department microsite) ---
    research_areas = db.Column(db.Text)
    publications = db.Column(db.Text)
    certifications = db.Column(db.Text)
    projects = db.Column(db.Text)
    awards = db.Column(db.Text)
    office_hours = db.Column(db.String(120))

    user = db.relationship("User", back_populates="teacher_profile")
    department = db.relationship("Department", foreign_keys=[department_id])
    subjects = db.relationship("Subject", back_populates="teacher")
    attendance_records = db.relationship("TeacherAttendance", back_populates="teacher", cascade="all, delete-orphan")


class TeacherAttendance(db.Model):
    __tablename__ = "teacher_attendance"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(12), default="Present")  # Present/Absent/Half Day/Leave
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)

    teacher = db.relationship("Teacher", back_populates="attendance_records")


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(10), nullable=False, default="Present")  # Present/Absent/Late/Leave
    marked_by = db.Column(db.Integer, db.ForeignKey("teachers.id"))

    student = db.relationship("Student", back_populates="attendance_records")
    subject = db.relationship("Subject")


# ---------------------------------------------------------------------------
# Assignments
# ---------------------------------------------------------------------------


class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    description = db.Column(db.Text)
    attachment = db.Column(db.String(255))
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship("Subject")
    submissions = db.relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")


class AssignmentSubmission(db.Model):
    __tablename__ = "assignment_submissions"

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    file_path = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignment = db.relationship("Assignment", back_populates="submissions")
    student = db.relationship("Student", back_populates="submissions")


class StudyMaterial(db.Model):
    __tablename__ = "study_materials"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    file_path = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    subject = db.relationship("Subject")


# ---------------------------------------------------------------------------
# Examination & marks
# ---------------------------------------------------------------------------


GRADE_TABLE = [
    (90, "O"), (80, "A+"), (70, "A"), (60, "B+"),
    (50, "B"), (40, "C"), (35, "P"), (0, "F"),
]


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    exam_hall = db.Column(db.String(50))
    exam_date = db.Column(db.Date)
    exam_time = db.Column(db.Time)

    course = db.relationship("Course")
    subject = db.relationship("Subject")


class Mark(db.Model):
    __tablename__ = "marks"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    internal_marks = db.Column(db.Float, default=0)
    external_marks = db.Column(db.Float, default=0)

    student = db.relationship("Student", back_populates="marks")
    subject = db.relationship("Subject")

    @property
    def total(self):
        return (self.internal_marks or 0) + (self.external_marks or 0)

    @property
    def result(self):
        return "Pass" if self.total >= 35 else "Fail"

    @property
    def grade(self):
        for cutoff, letter in GRADE_TABLE:
            if self.total >= cutoff:
                return letter
        return "F"


# ---------------------------------------------------------------------------
# Fees & payments
# ---------------------------------------------------------------------------


class Fee(db.Model):
    __tablename__ = "fees"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    fee_name = db.Column(db.String(100), nullable=False)  # College Fee, Exam Fee, Custom...
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    paid_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    pending_method = db.Column(db.String(10))  # 'Cash' or 'Online' while awaiting admin confirmation
    pending_at = db.Column(db.DateTime)

    student = db.relationship("Student", back_populates="fees")
    payments = db.relationship("Payment", back_populates="fee", cascade="all, delete-orphan")

    @property
    def remaining(self):
        return float(self.amount or 0) - float(self.paid_amount or 0)

    @property
    def is_paid(self):
        return self.remaining <= 0

    @property
    def is_awaiting_confirmation(self):
        return bool(self.pending_method) and not self.is_paid


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    fee_id = db.Column(db.Integer, db.ForeignKey("fees.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_on = db.Column(db.DateTime, default=datetime.utcnow)
    receipt_no = db.Column(db.String(40), unique=True)

    fee = db.relationship("Fee", back_populates="payments")


# ---------------------------------------------------------------------------
# Timetable / events / notices
# ---------------------------------------------------------------------------


class Timetable(db.Model):
    __tablename__ = "timetables"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False)  # Monday..Saturday
    period = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)

    department = db.relationship("Department")
    subject = db.relationship("Subject")


class Notice(db.Model):
    __tablename__ = "notices"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text)
    posted_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))  # null = college-wide

    author = db.relationship("User")
    department = db.relationship("Department")


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(30), nullable=False)  # College Event/Workshop/Seminar/Sports
    description = db.Column(db.Text)
    event_date = db.Column(db.Date)
    location = db.Column(db.String(120))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))  # null = college-wide

    department = db.relationship("Department")


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(15), default="Pending")  # Pending/Approved/Rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("Student", back_populates="leave_requests")


# ---------------------------------------------------------------------------
# Library & transport
# ---------------------------------------------------------------------------


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(120))
    isbn = db.Column(db.String(30))
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)

    issues = db.relationship("BookIssue", back_populates="book", cascade="all, delete-orphan")


class BookIssue(db.Model):
    __tablename__ = "book_issues"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    issue_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date)
    return_date = db.Column(db.Date)
    fine_amount = db.Column(db.Numeric(8, 2), default=0)

    book = db.relationship("Book", back_populates="issues")
    student = db.relationship("Student")


class Bus(db.Model):
    __tablename__ = "buses"

    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(20), nullable=False)
    route = db.Column(db.String(150))
    driver_name = db.Column(db.String(120))
    driver_phone = db.Column(db.String(20))
    driver_photo = db.Column(db.String(255))


# ---------------------------------------------------------------------------
# Department microsite (Overview/History/HOD/Labs/Achievements/Placements/
# Downloads/Contact — the rest of the sections reuse existing models:
# Faculty=Teacher, Staff=Employee, Courses=Subject, Students=Student,
# Events=Event, Notices=Notice, Timetable=Timetable)
# ---------------------------------------------------------------------------


LAB_INCHARGE_LABEL = "Lab Incharge"


class Laboratory(db.Model):
    __tablename__ = "laboratories"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    incharge_teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    equipment_list = db.Column(db.Text)
    num_systems = db.Column(db.Integer, default=0)
    software_installed = db.Column(db.Text)
    timetable_note = db.Column(db.Text)

    department = db.relationship("Department", back_populates="labs")
    incharge = db.relationship("Teacher")


ACHIEVEMENT_CATEGORIES = [
    "Faculty Award", "Student Award", "Research Publication", "Patent",
    "Hackathon", "Competition",
]


class DepartmentAchievement(db.Model):
    __tablename__ = "department_achievements"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text)
    achieved_on = db.Column(db.Date)

    department = db.relationship("Department", back_populates="dept_achievements")


class PlacementRecord(db.Model):
    __tablename__ = "placement_records"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    company = db.Column(db.String(150), nullable=False)
    package = db.Column(db.Numeric(10, 2))
    year = db.Column(db.Integer)
    notes = db.Column(db.String(255))

    department = db.relationship("Department", back_populates="placement_records")
    student = db.relationship("Student")


DOCUMENT_CATEGORIES = [
    "Syllabus", "Academic Calendar", "Timetable", "Lab Manual",
    "Assignment", "Question Paper",
]


class DepartmentDocument(db.Model):
    __tablename__ = "department_documents"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    file_path = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship("Department", back_populates="documents")


class DepartmentContactMessage(db.Model):
    __tablename__ = "department_contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship("Department", back_populates="contact_messages")


# ---------------------------------------------------------------------------
# Employee / HR module (non-teaching staff)
# ---------------------------------------------------------------------------


EMPLOYEE_DESIGNATIONS = [
    "Principal", "Vice Principal", "HOD (Head of Department)", "Librarian",
    "Accountant", "Office Staff", "Lab Assistant", "Receptionist",
    "Hostel Warden", "Transport Manager", "Bus Driver", "Security Guard",
    "Cleaner/Housekeeping", "IT Administrator", "Placement Officer",
    "Sports Coach", "Nurse/Medical Staff",
]

EMPLOYMENT_TYPES = ["Permanent", "Contract"]


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    employee_code = db.Column(db.String(30), unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    designation = db.Column(db.String(50))
    qualification = db.Column(db.String(120))
    experience_years = db.Column(db.Integer, default=0)
    joining_date = db.Column(db.Date, default=date.today)
    salary = db.Column(db.Numeric(10, 2), default=0)
    employment_type = db.Column(db.String(20), default="Permanent")
    status = db.Column(db.String(15), default="Active")
    address = db.Column(db.String(255))

    user = db.relationship("User")
    department = db.relationship("Department")
    attendance_records = db.relationship("EmployeeAttendance", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = db.relationship("EmployeeLeaveRequest", back_populates="employee", cascade="all, delete-orphan")


class EmployeeAttendance(db.Model):
    __tablename__ = "employee_attendance"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(12), default="Present")  # Present/Absent/Half Day/Leave
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)

    employee = db.relationship("Employee", back_populates="attendance_records")


class EmployeeLeaveRequest(db.Model):
    __tablename__ = "employee_leave_requests"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(15), default="Pending")  # Pending/Approved/Rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship("Employee", back_populates="leave_requests")
