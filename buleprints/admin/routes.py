import csv
import io
from datetime import date, datetime, timedelta

from flask import (
    render_template, redirect, url_for, flash, request, Response, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import (
    User, Student, Teacher, Course, Department, ClassGroup, Subject,
    Attendance, Fee, Payment, Notice, TEACHER_DESIGNATIONS,
    Exam, Timetable, Event, Book, BookIssue, Bus, LeaveRequest, Mark, Assignment,
    AssignmentSubmission, Employee, EmployeeAttendance, EmployeeLeaveRequest,
    EMPLOYEE_DESIGNATIONS, EMPLOYMENT_TYPES, TeacherAttendance,
)
from utils import roles_required, save_photo, generate_code, parse_date
from . import admin_bp


@admin_bp.before_request
@login_required
@roles_required("admin")
def guard():
    """Every admin route requires an authenticated admin user."""
    pass


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@admin_bp.route("/dashboard")
def dashboard():
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()

    dept_counts = (
        db.session.query(Department.name, func.count(Student.id))
        .outerjoin(Student, Student.department_id == Department.id)
        .group_by(Department.id)
        .all()
    )

    ug_count = (
        db.session.query(func.count(Student.id))
        .join(Course, Student.course_id == Course.id)
        .filter(Course.level == "UG")
        .scalar() or 0
    )
    pg_count = (
        db.session.query(func.count(Student.id))
        .join(Course, Student.course_id == Course.id)
        .filter(Course.level == "PG")
        .scalar() or 0
    )

    total_branches = Department.query.count()
    total_classes = ClassGroup.query.count()
    total_courses = Course.query.count()

    all_fees = Fee.query.all()
    total_fee_expected = sum(float(f.amount or 0) for f in all_fees)
    total_fee_collected = sum(float(f.paid_amount or 0) for f in all_fees)
    students_fully_paid = sum(1 for f in all_fees if f.is_paid)
    students_pending_fees = sum(1 for f in all_fees if not f.is_paid)

    exam_fees = [f for f in all_fees if "exam" in f.fee_name.lower()]
    exam_fee_paid = sum(1 for f in exam_fees if f.is_paid)
    exam_fee_pending = sum(1 for f in exam_fees if not f.is_paid)

    course_wise = (
        db.session.query(Course.name, func.count(Student.id))
        .outerjoin(Student, Student.course_id == Course.id)
        .group_by(Course.id)
        .all()
    )

    total_present = Attendance.query.filter_by(status="Present").count()
    total_attendance = Attendance.query.count()
    attendance_pct = round((total_present / total_attendance) * 100, 1) if total_attendance else 0

    student_growth = (
        db.session.query(func.strftime("%Y-%m", Student.admission_date), func.count(Student.id))
        .group_by(func.strftime("%Y-%m", Student.admission_date))
        .order_by(func.strftime("%Y-%m", Student.admission_date))
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        total_teachers=total_teachers,
        dept_counts=dept_counts,
        ug_count=ug_count,
        pg_count=pg_count,
        total_branches=total_branches,
        total_classes=total_classes,
        total_courses=total_courses,
        total_fee_expected=total_fee_expected,
        total_fee_collected=total_fee_collected,
        students_fully_paid=students_fully_paid,
        students_pending_fees=students_pending_fees,
        exam_fee_paid=exam_fee_paid,
        exam_fee_pending=exam_fee_pending,
        course_wise=course_wise,
        attendance_pct=attendance_pct,
        student_growth=student_growth,
    )


# ---------------------------------------------------------------------------
# Student management
# ---------------------------------------------------------------------------


@admin_bp.route("/students")
def students_list():
    q = request.args.get("q", "").strip()
    query = Student.query.join(User)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (User.full_name.ilike(like)) | (Student.student_code.ilike(like)) | (User.email.ilike(like))
        )
    students = query.order_by(Student.id.desc()).all()
    return render_template("admin/students_list.html", students=students, q=q)


@admin_bp.route("/students/export")
def students_export():
    students = Student.query.join(User).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Email", "Phone", "Course", "Department", "Semester", "Status"])
    for s in students:
        writer.writerow([
            s.student_code, s.user.full_name, s.user.email, s.user.phone,
            s.course.name if s.course else "", s.department.name if s.department else "",
            s.semester, s.status,
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"},
    )


@admin_bp.route("/students/add", methods=["GET", "POST"])
def students_add():
    courses = Course.query.all()
    departments = Department.query.all()
    classes = ClassGroup.query.all()

    if request.method == "POST":
        f = request.form
        password = f.get("password") or "changeme123"
        confirm_password = f.get("confirm_password") or password
        if password != confirm_password:
            flash("Password and Confirm Password do not match.", "danger")
            return redirect(url_for("admin.students_add"))

        photo_path = save_photo(request.files.get("photo"))

        user = User(
            full_name=f["full_name"].strip(),
            username=f["username"].strip(),
            email=f["email"].strip().lower(),
            phone=f.get("phone", "").strip(),
            dob=parse_date(f.get("dob")),
            gender=f.get("gender"),
            photo=photo_path,
            role="student",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            blood_group=f.get("blood_group"),
            address=f.get("address"),
            parent_name=f.get("parent_name"),
            parent_phone=f.get("parent_phone"),
            course_id=f.get("course_id") or None,
            department_id=f.get("department_id") or None,
            class_group_id=f.get("class_group_id") or None,
            semester=f.get("semester") or None,
            admission_date=parse_date(f.get("admission_date")) or date.today(),
            status=f.get("status", "Active"),
        )
        db.session.add(student)
        db.session.flush()
        student.student_code = generate_code("STU", student.id)

        # Auto-generate the College Fee: UG students are billed by department,
        # PG students (MBA/MCA, no departments) are billed directly by course.
        college_fee_amount = None
        if student.department_id:
            dept = Department.query.get(int(student.department_id))
            if dept:
                college_fee_amount = dept.fee_amount
        elif student.course_id:
            course = Course.query.get(int(student.course_id))
            if course and not course.has_departments:
                college_fee_amount = course.fee_amount

        if college_fee_amount and float(college_fee_amount) > 0:
            db.session.add(Fee(
                student_id=student.id, fee_name="College Fee",
                amount=college_fee_amount, paid_amount=0,
            ))

        db.session.commit()
        flash(f"Student {user.full_name} added successfully.", "success")
        return redirect(url_for("admin.students_list"))

    return render_template(
        "admin/student_form.html", courses=courses, departments=departments,
        classes=classes, student=None,
        prefill_department_id=request.args.get("department_id", type=int),
        prefill_semester=request.args.get("semester", type=int),
        prefill_course_id=request.args.get("course_id", type=int),
    )


@admin_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def students_edit(student_id):
    student = Student.query.get_or_404(student_id)
    courses = Course.query.all()
    departments = Department.query.all()
    classes = ClassGroup.query.all()

    if request.method == "POST":
        f = request.form
        student.user.full_name = f["full_name"].strip()
        student.user.email = f["email"].strip().lower()
        student.user.phone = f.get("phone", "").strip()
        student.blood_group = f.get("blood_group")
        student.address = f.get("address")
        student.parent_name = f.get("parent_name")
        student.parent_phone = f.get("parent_phone")
        student.course_id = f.get("course_id") or None
        student.department_id = f.get("department_id") or None
        student.class_group_id = f.get("class_group_id") or None
        student.semester = f.get("semester") or None
        student.status = f.get("status", "Active")
        new_photo = save_photo(request.files.get("photo"))
        if new_photo:
            student.user.photo = new_photo
        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("admin.students_list"))

    return render_template(
        "admin/student_form.html", courses=courses, departments=departments,
        classes=classes, student=student,
    )


@admin_bp.route("/students/<int:student_id>/delete", methods=["POST"])
def students_delete(student_id):
    student = Student.query.get_or_404(student_id)
    user = student.user
    db.session.delete(student)
    db.session.delete(user)
    db.session.commit()
    flash("Student deleted.", "info")
    return redirect(url_for("admin.students_list"))


@admin_bp.route("/students/<int:student_id>")
def students_view(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template("admin/student_view.html", student=student)


# ---------------------------------------------------------------------------
# Teacher management
# ---------------------------------------------------------------------------


@admin_bp.route("/teachers")
def teachers_list():
    teachers = Teacher.query.join(User).order_by(Teacher.id.desc()).all()
    return render_template("admin/teachers_list.html", teachers=teachers)


@admin_bp.route("/teachers/add", methods=["GET", "POST"])
def teachers_add():
    departments = Department.query.all()
    subjects = Subject.query.all()

    if request.method == "POST":
        f = request.form
        password = f.get("password") or "changeme123"
        confirm_password = f.get("confirm_password") or password
        if password != confirm_password:
            flash("Password and Confirm Password do not match.", "danger")
            return redirect(url_for("admin.teachers_add"))

        user = User(
            full_name=f["full_name"].strip(),
            username=f["username"].strip(),
            email=f["email"].strip().lower(),
            phone=f.get("phone", "").strip(),
            role="teacher",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        teacher = Teacher(
            user_id=user.id,
            qualification=f.get("qualification"),
            department_id=f.get("department_id") or None,
            designation=f.get("designation"),
            experience_years=f.get("experience_years") or 0,
        )
        db.session.add(teacher)
        db.session.flush()
        teacher.teacher_code = generate_code("TCH", teacher.id)

        subject_id = f.get("subject_id")
        if subject_id:
            subj = Subject.query.get(int(subject_id))
            if subj:
                subj.teacher_id = teacher.id

        db.session.commit()
        flash(f"Teacher {user.full_name} added successfully.", "success")
        return redirect(url_for("admin.teachers_list"))

    return render_template(
        "admin/teacher_form.html", departments=departments, subjects=subjects,
        designations=TEACHER_DESIGNATIONS, teacher=None,
    )


@admin_bp.route("/teachers/<int:teacher_id>")
def teachers_view(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    recent_attendance = sorted(teacher.attendance_records, key=lambda r: r.date, reverse=True)[:15]
    return render_template("admin/teacher_view.html", teacher=teacher, recent_attendance=recent_attendance)


@admin_bp.route("/teachers/<int:teacher_id>/edit", methods=["GET", "POST"])
def teachers_edit(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    departments = Department.query.all()
    subjects = Subject.query.all()

    if request.method == "POST":
        f = request.form
        teacher.user.full_name = f["full_name"].strip()
        teacher.user.email = f["email"].strip().lower()
        teacher.user.phone = f.get("phone", "").strip()
        teacher.qualification = f.get("qualification")
        teacher.department_id = f.get("department_id") or None
        teacher.designation = f.get("designation")
        teacher.experience_years = f.get("experience_years") or 0
        teacher.cabin_number = f.get("cabin_number")
        teacher.office_hours = f.get("office_hours")
        teacher.research_areas = f.get("research_areas")
        teacher.publications = f.get("publications")
        teacher.certifications = f.get("certifications")
        teacher.projects = f.get("projects")
        teacher.awards = f.get("awards")

        subject_id = f.get("subject_id")
        if subject_id:
            subj = Subject.query.get(int(subject_id))
            if subj:
                subj.teacher_id = teacher.id

        db.session.commit()
        flash("Teacher updated.", "success")
        return redirect(url_for("admin.teachers_list"))

    return render_template(
        "admin/teacher_form.html", departments=departments, subjects=subjects,
        designations=TEACHER_DESIGNATIONS, teacher=teacher,
    )


@admin_bp.route("/teachers/<int:teacher_id>/delete", methods=["POST"])
def teachers_delete(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    user = teacher.user
    db.session.delete(teacher)
    db.session.delete(user)
    db.session.commit()
    flash("Teacher deleted.", "info")
    return redirect(url_for("admin.teachers_list"))


# ---------------------------------------------------------------------------
# Course management
# ---------------------------------------------------------------------------


@admin_bp.route("/courses")
def courses_list():
    courses = Course.query.all()
    return render_template("admin/courses_list.html", courses=courses)


@admin_bp.route("/courses/add", methods=["GET", "POST"])
def courses_add():
    if request.method == "POST":
        f = request.form
        course = Course(
            name=f["name"].strip(),
            level=f["level"],
            duration_years=f.get("duration_years") or 4,
            fee_amount=f.get("fee_amount") or 0,
            has_departments=(f.get("level") == "UG"),
        )
        db.session.add(course)
        db.session.commit()
        flash("Course added.", "success")
        return redirect(url_for("admin.courses_list"))
    return render_template("admin/course_form.html")


@admin_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
def courses_edit(course_id):
    course = Course.query.get_or_404(course_id)
    if request.method == "POST":
        f = request.form
        course.name = f["name"].strip()
        course.level = f["level"]
        course.duration_years = f.get("duration_years") or 4
        course.fee_amount = f.get("fee_amount") or 0
        course.has_departments = (f.get("level") == "UG")
        db.session.commit()
        flash("Course updated.", "success")
        return redirect(url_for("admin.courses_list"))
    return render_template("admin/course_form.html", course=course)


@admin_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
def courses_delete(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash("Course deleted.", "info")
    return redirect(url_for("admin.courses_list"))


@admin_bp.route("/courses/<int:course_id>/view")
def courses_view(course_id):
    course = Course.query.get_or_404(course_id)
    if course.has_departments:
        # UG course: drill down into its Departments (which then drill into semesters).
        departments = Department.query.filter_by(course_id=course.id).all()
        return render_template("admin/course_view_departments.html", course=course, departments=departments)

    # PG course (no departments): drill straight into semesters.
    num_semesters = max((course.duration_years or 2) * 2, 1)
    semesters = range(1, num_semesters + 1)
    counts = {
        sem: Student.query.filter_by(course_id=course.id, semester=sem).count()
        for sem in semesters
    }
    total = Student.query.filter_by(course_id=course.id).count()
    return render_template(
        "admin/course_view_semesters.html", course=course, semesters=semesters, counts=counts, total=total,
    )


@admin_bp.route("/courses/<int:course_id>/semester/<int:sem>")
def courses_semester_students(course_id, sem):
    course = Course.query.get_or_404(course_id)
    students = (
        Student.query.filter_by(course_id=course.id, semester=sem)
        .join(User).order_by(User.full_name).all()
    )
    return render_template("admin/course_semester_students.html", course=course, semester=sem, students=students)


# ---------------------------------------------------------------------------
# Department management
# ---------------------------------------------------------------------------


@admin_bp.route("/departments")
def departments_list():
    departments = Department.query.join(Course).all()
    return render_template("admin/departments_list.html", departments=departments)


@admin_bp.route("/departments/add", methods=["GET", "POST"])
def departments_add():
    courses = Course.query.filter_by(has_departments=True).all()
    if request.method == "POST":
        f = request.form
        dept = Department(
            name=f["name"].strip(),
            course_id=f["course_id"],
            fee_amount=f.get("fee_amount") or 0,
        )
        db.session.add(dept)
        db.session.commit()
        flash("Department added.", "success")
        return redirect(url_for("admin.departments_list"))
    return render_template("admin/department_form.html", courses=courses)


@admin_bp.route("/departments/<int:dept_id>/edit", methods=["GET", "POST"])
def departments_edit(dept_id):
    dept = Department.query.get_or_404(dept_id)
    courses = Course.query.filter_by(has_departments=True).all()
    if request.method == "POST":
        f = request.form
        dept.name = f["name"].strip()
        dept.course_id = f["course_id"]
        dept.fee_amount = f.get("fee_amount") or 0
        db.session.commit()
        flash("Department updated.", "success")
        return redirect(url_for("admin.departments_list"))
    return render_template("admin/department_form.html", courses=courses, department=dept)


@admin_bp.route("/departments/<int:dept_id>/delete", methods=["POST"])
def departments_delete(dept_id):
    dept = Department.query.get_or_404(dept_id)
    db.session.delete(dept)
    db.session.commit()
    flash("Department deleted.", "info")
    return redirect(url_for("admin.departments_list"))


@admin_bp.route("/departments/<int:dept_id>/view")
def departments_view(dept_id):
    dept = Department.query.get_or_404(dept_id)
    semesters = range(1, 9)
    counts = {
        sem: Student.query.filter_by(department_id=dept.id, semester=sem).count()
        for sem in semesters
    }
    total = Student.query.filter_by(department_id=dept.id).count()
    return render_template("admin/department_view.html", department=dept, semesters=semesters, counts=counts, total=total)


@admin_bp.route("/departments/<int:dept_id>/semester/<int:sem>")
def departments_semester_students(dept_id, sem):
    dept = Department.query.get_or_404(dept_id)
    students = (
        Student.query.filter_by(department_id=dept.id, semester=sem)
        .join(User).order_by(User.full_name).all()
    )
    return render_template("admin/department_semester_students.html", department=dept, semester=sem, students=students)


# ---------------------------------------------------------------------------
# Subject management
# ---------------------------------------------------------------------------


@admin_bp.route("/subjects")
def subjects_list():
    subjects = Subject.query.join(Department).all()
    return render_template("admin/subjects_list.html", subjects=subjects)


@admin_bp.route("/subjects/add", methods=["GET", "POST"])
def subjects_add():
    departments = Department.query.all()
    teachers = Teacher.query.join(User).all()
    if request.method == "POST":
        f = request.form
        subject = Subject(
            name=f["name"].strip(),
            code=f.get("code"),
            department_id=f["department_id"],
            semester=f.get("semester") or None,
            credit_hours=f.get("credit_hours") or 3,
            teacher_id=f.get("teacher_id") or None,
        )
        db.session.add(subject)
        db.session.commit()
        flash("Subject added.", "success")
        return redirect(url_for("admin.subjects_list"))
    return render_template("admin/subject_form.html", departments=departments, teachers=teachers)


@admin_bp.route("/subjects/<int:subject_id>/edit", methods=["GET", "POST"])
def subjects_edit(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    departments = Department.query.all()
    teachers = Teacher.query.join(User).all()
    if request.method == "POST":
        f = request.form
        subject.name = f["name"].strip()
        subject.code = f.get("code")
        subject.department_id = f["department_id"]
        subject.semester = f.get("semester") or None
        subject.credit_hours = f.get("credit_hours") or 3
        subject.teacher_id = f.get("teacher_id") or None
        db.session.commit()
        flash("Subject updated.", "success")
        return redirect(url_for("admin.subjects_list"))
    return render_template("admin/subject_form.html", departments=departments, teachers=teachers, subject=subject)


@admin_bp.route("/subjects/<int:subject_id>/delete", methods=["POST"])
def subjects_delete(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted.", "info")
    return redirect(url_for("admin.subjects_list"))


# ---------------------------------------------------------------------------
# Fees
# ---------------------------------------------------------------------------


@admin_bp.route("/fees")
def fees_list():
    fees = Fee.query.join(Student).all()
    return render_template("admin/fees_list.html", fees=fees)


@admin_bp.route("/fees/add", methods=["GET", "POST"])
def fees_add():
    students = Student.query.join(User).all()
    if request.method == "POST":
        f = request.form
        fee = Fee(
            student_id=f["student_id"],
            fee_name=f["fee_name"].strip(),
            amount=f["amount"],
            start_date=parse_date(f.get("start_date")),
            end_date=parse_date(f.get("end_date")),
        )
        db.session.add(fee)
        db.session.commit()
        flash("Fee added.", "success")
        return redirect(url_for("admin.fees_list"))
    return render_template("admin/fee_form.html", students=students)


@admin_bp.route("/fees/<int:fee_id>/confirm", methods=["POST"])
def fees_confirm(fee_id):
    """Admin confirms a student's fee payment (cash paid at office/bank, or online)."""
    fee = Fee.query.get_or_404(fee_id)
    method = fee.pending_method or "Cash"
    db.session.add(Payment(
        fee_id=fee.id, amount=fee.remaining,
        receipt_no=f"RCPT{fee.id:05d}{int(datetime.utcnow().timestamp())}",
    ))
    fee.paid_amount = fee.amount
    fee.pending_method = None
    fee.pending_at = None
    db.session.commit()
    flash(f"Payment confirmed for {fee.student.user.full_name} ({fee.fee_name}) via {method}.", "success")
    return redirect(url_for("admin.fees_list"))


# ---------------------------------------------------------------------------
# Teachers CSV export
# ---------------------------------------------------------------------------


@admin_bp.route("/teachers/export")
def teachers_export():
    teachers = Teacher.query.join(User).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Teacher ID", "Name", "Email", "Phone", "Designation", "Department", "Subjects", "Experience"])
    for t in teachers:
        writer.writerow([
            t.teacher_code, t.user.full_name, t.user.email, t.user.phone,
            t.designation, t.department.name if t.department else "",
            ", ".join(s.name for s in t.subjects), t.experience_years,
        ])
    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=teachers.csv"},
    )


# ---------------------------------------------------------------------------
# Teacher attendance (admin tracks teaching-staff attendance)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Teacher attendance — teachers mark their own; admin can only view/export it.
# ---------------------------------------------------------------------------


@admin_bp.route("/teachers/attendance")
def teacher_attendance_take():
    # Admin no longer marks teacher attendance directly — teachers self-report
    # via their own portal. This redirects to the read-only report/export view.
    return redirect(url_for("admin.teacher_attendance_report", **request.args))


@admin_bp.route("/teachers/attendance/report")
def teacher_attendance_report():
    month = request.args.get("month")
    query = TeacherAttendance.query.join(Teacher)
    if month:
        query = query.filter(func.strftime("%Y-%m", TeacherAttendance.date) == month)
    records = query.order_by(TeacherAttendance.date.desc()).limit(500).all()
    return render_template("admin/teacher_attendance_report.html", records=records, month=month)


@admin_bp.route("/teachers/attendance/export")
def teacher_attendance_export():
    month = request.args.get("month")
    query = TeacherAttendance.query.join(Teacher)
    if month:
        query = query.filter(func.strftime("%Y-%m", TeacherAttendance.date) == month)
    records = query.order_by(TeacherAttendance.date).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Teacher", "Status", "Check In", "Check Out"])
    for r in records:
        writer.writerow([r.date, r.teacher.user.full_name, r.status, r.check_in or "", r.check_out or ""])
    label = month or "all"
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": f"attachment; filename=teacher_attendance_{label}.csv"})


# ---------------------------------------------------------------------------
# Notices
# ---------------------------------------------------------------------------


@admin_bp.route("/notices")
def notices_list():
    notices = Notice.query.order_by(Notice.posted_at.desc()).all()
    return render_template("admin/notices_list.html", notices=notices)


@admin_bp.route("/notices/<int:notice_id>/edit", methods=["GET", "POST"])
def notices_edit(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    if request.method == "POST":
        f = request.form
        notice.title = f["title"].strip()
        notice.content = f.get("content")
        db.session.commit()
        flash("Notice updated.", "success")
        return redirect(url_for("admin.notices_list"))
    return render_template("admin/notice_form.html", notice=notice)



@admin_bp.route("/notices/add", methods=["GET", "POST"])
def notices_add():
    if request.method == "POST":
        f = request.form
        notice = Notice(title=f["title"].strip(), content=f.get("content"), posted_by=current_user.id)
        db.session.add(notice)
        db.session.commit()
        flash("Notice posted.", "success")
        return redirect(url_for("admin.notices_list"))
    return render_template("admin/notice_form.html")


@admin_bp.route("/notices/<int:notice_id>/delete", methods=["POST"])
def notices_delete(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash("Notice deleted.", "info")
    return redirect(url_for("admin.notices_list"))


# ---------------------------------------------------------------------------
# Attendance report (department-wise, exportable)
# ---------------------------------------------------------------------------


@admin_bp.route("/attendance")
def attendance_report():
    departments = Department.query.all()
    department_id = request.args.get("department_id", type=int)
    month = request.args.get("month")  # 'YYYY-MM'

    query = Attendance.query.join(Student)
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if month:
        query = query.filter(func.strftime("%Y-%m", Attendance.date) == month)
    records = query.order_by(Attendance.date.desc()).limit(500).all()

    return render_template(
        "admin/attendance_report.html", departments=departments, records=records,
        department_id=department_id, month=month,
    )


@admin_bp.route("/attendance/export")
def attendance_export():
    department_id = request.args.get("department_id", type=int)
    month = request.args.get("month")

    query = Attendance.query.join(Student)
    if department_id:
        query = query.filter(Student.department_id == department_id)
    if month:
        query = query.filter(func.strftime("%Y-%m", Attendance.date) == month)
    records = query.order_by(Attendance.date).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Student", "Department", "Subject", "Status"])
    for r in records:
        writer.writerow([
            r.date, r.student.user.full_name,
            r.student.department.name if r.student.department else "",
            r.subject.name, r.status,
        ])
    label = month or "all"
    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{label}.csv"},
    )


# ---------------------------------------------------------------------------
# Examination Module
# ---------------------------------------------------------------------------


@admin_bp.route("/exams")
def exams_list():
    exams = Exam.query.join(Course).order_by(Exam.exam_date).all()
    return render_template("admin/exams_list.html", exams=exams)


@admin_bp.route("/exams/add", methods=["GET", "POST"])
def exams_add():
    courses = Course.query.all()
    subjects = Subject.query.all()
    if request.method == "POST":
        f = request.form
        exam_time = None
        if f.get("exam_time"):
            exam_time = datetime.strptime(f["exam_time"], "%H:%M").time()
        exam = Exam(
            name=f["name"].strip(),
            course_id=f["course_id"],
            subject_id=f.get("subject_id") or None,
            exam_hall=f.get("exam_hall"),
            exam_date=parse_date(f.get("exam_date")),
            exam_time=exam_time,
        )
        db.session.add(exam)
        db.session.commit()
        flash("Exam scheduled.", "success")
        return redirect(url_for("admin.exams_list"))
    return render_template("admin/exam_form.html", courses=courses, subjects=subjects, exam=None)


@admin_bp.route("/exams/<int:exam_id>/edit", methods=["GET", "POST"])
def exams_edit(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    courses = Course.query.all()
    subjects = Subject.query.all()
    if request.method == "POST":
        f = request.form
        exam.name = f["name"].strip()
        exam.course_id = f["course_id"]
        exam.subject_id = f.get("subject_id") or None
        exam.exam_hall = f.get("exam_hall")
        exam.exam_date = parse_date(f.get("exam_date"))
        exam.exam_time = datetime.strptime(f["exam_time"], "%H:%M").time() if f.get("exam_time") else None
        db.session.commit()
        flash("Exam updated.", "success")
        return redirect(url_for("admin.exams_list"))
    return render_template("admin/exam_form.html", courses=courses, subjects=subjects, exam=exam)


@admin_bp.route("/exams/<int:exam_id>/delete", methods=["POST"])
def exams_delete(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    db.session.delete(exam)
    db.session.commit()
    flash("Exam deleted.", "info")
    return redirect(url_for("admin.exams_list"))


# ---------------------------------------------------------------------------
# Timetable Management (weekly department timetable)
# ---------------------------------------------------------------------------


@admin_bp.route("/timetables")
def timetables_list():
    department_id = request.args.get("department_id", type=int)
    departments = Department.query.all()
    query = Timetable.query.join(Department)
    if department_id:
        query = query.filter(Timetable.department_id == department_id)
    entries = query.order_by(Timetable.day_of_week, Timetable.period).all()
    return render_template(
        "admin/timetables_list.html", entries=entries, departments=departments, department_id=department_id,
    )


@admin_bp.route("/timetables/add", methods=["GET", "POST"])
def timetables_add():
    departments = Department.query.all()
    subjects = Subject.query.all()
    if request.method == "POST":
        f = request.form
        entry = Timetable(
            department_id=f["department_id"],
            day_of_week=f["day_of_week"],
            period=f["period"],
            subject_id=f.get("subject_id") or None,
            start_time=datetime.strptime(f["start_time"], "%H:%M").time() if f.get("start_time") else None,
            end_time=datetime.strptime(f["end_time"], "%H:%M").time() if f.get("end_time") else None,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Timetable entry added.", "success")
        return redirect(url_for("admin.timetables_list"))
    return render_template("admin/timetable_form.html", departments=departments, subjects=subjects, entry=None)


@admin_bp.route("/timetables/<int:entry_id>/edit", methods=["GET", "POST"])
def timetables_edit(entry_id):
    entry = Timetable.query.get_or_404(entry_id)
    departments = Department.query.all()
    subjects = Subject.query.all()
    if request.method == "POST":
        f = request.form
        entry.department_id = f["department_id"]
        entry.day_of_week = f["day_of_week"]
        entry.period = f["period"]
        entry.subject_id = f.get("subject_id") or None
        entry.start_time = datetime.strptime(f["start_time"], "%H:%M").time() if f.get("start_time") else None
        entry.end_time = datetime.strptime(f["end_time"], "%H:%M").time() if f.get("end_time") else None
        db.session.commit()
        flash("Timetable entry updated.", "success")
        return redirect(url_for("admin.timetables_list"))
    return render_template("admin/timetable_form.html", departments=departments, subjects=subjects, entry=entry)


@admin_bp.route("/timetables/<int:entry_id>/delete", methods=["POST"])
def timetables_delete(entry_id):
    entry = Timetable.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("Timetable entry deleted.", "info")
    return redirect(url_for("admin.timetables_list"))


# ---------------------------------------------------------------------------
# Event Management (College Events / Workshops / Seminars / Sports)
# ---------------------------------------------------------------------------


EVENT_CATEGORIES = ["College Event", "Workshop", "Seminar", "Sports"]


@admin_bp.route("/events")
def events_list():
    events = Event.query.order_by(Event.event_date.desc()).all()
    return render_template("admin/events_list.html", events=events, categories=EVENT_CATEGORIES)


@admin_bp.route("/events/add", methods=["GET", "POST"])
def events_add():
    if request.method == "POST":
        f = request.form
        event = Event(
            title=f["title"].strip(), category=f["category"],
            description=f.get("description"), event_date=parse_date(f.get("event_date")),
            location=f.get("location"),
        )
        db.session.add(event)
        db.session.commit()
        flash("Event added.", "success")
        return redirect(url_for("admin.events_list"))
    return render_template("admin/event_form.html", categories=EVENT_CATEGORIES, event=None)


@admin_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
def events_edit(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == "POST":
        f = request.form
        event.title = f["title"].strip()
        event.category = f["category"]
        event.description = f.get("description")
        event.event_date = parse_date(f.get("event_date"))
        event.location = f.get("location")
        db.session.commit()
        flash("Event updated.", "success")
        return redirect(url_for("admin.events_list"))
    return render_template("admin/event_form.html", categories=EVENT_CATEGORIES, event=event)


@admin_bp.route("/events/<int:event_id>/delete", methods=["POST"])
def events_delete(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.", "info")
    return redirect(url_for("admin.events_list"))


# ---------------------------------------------------------------------------
# Library Module
# ---------------------------------------------------------------------------


@admin_bp.route("/library/books")
def books_list():
    q = request.args.get("q", "").strip()
    query = Book.query
    if q:
        like = f"%{q}%"
        query = query.filter((Book.title.ilike(like)) | (Book.author.ilike(like)) | (Book.isbn.ilike(like)))
    books = query.order_by(Book.title).all()
    return render_template("admin/books_list.html", books=books, q=q)


@admin_bp.route("/library/books/add", methods=["GET", "POST"])
def books_add():
    if request.method == "POST":
        f = request.form
        copies = int(f.get("total_copies") or 1)
        book = Book(
            title=f["title"].strip(), author=f.get("author"), isbn=f.get("isbn"),
            total_copies=copies, available_copies=copies,
        )
        db.session.add(book)
        db.session.commit()
        flash("Book added.", "success")
        return redirect(url_for("admin.books_list"))
    return render_template("admin/book_form.html", book=None)


@admin_bp.route("/library/books/<int:book_id>/edit", methods=["GET", "POST"])
def books_edit(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == "POST":
        f = request.form
        old_total = book.total_copies
        new_total = int(f.get("total_copies") or 1)
        book.title = f["title"].strip()
        book.author = f.get("author")
        book.isbn = f.get("isbn")
        book.total_copies = new_total
        book.available_copies = max(0, book.available_copies + (new_total - old_total))
        db.session.commit()
        flash("Book updated.", "success")
        return redirect(url_for("admin.books_list"))
    return render_template("admin/book_form.html", book=book)


@admin_bp.route("/library/books/<int:book_id>/delete", methods=["POST"])
def books_delete(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash("Book deleted.", "info")
    return redirect(url_for("admin.books_list"))


@admin_bp.route("/library/issues")
def book_issues_list():
    issues = BookIssue.query.order_by(BookIssue.issue_date.desc()).all()
    return render_template("admin/book_issues_list.html", issues=issues)


@admin_bp.route("/library/issue", methods=["GET", "POST"])
def book_issue_add():
    books = Book.query.filter(Book.available_copies > 0).all()
    students = Student.query.join(User).all()
    if request.method == "POST":
        f = request.form
        book = Book.query.get_or_404(int(f["book_id"]))
        if book.available_copies < 1:
            flash("No copies available for this book.", "danger")
            return redirect(url_for("admin.book_issue_add"))
        issue = BookIssue(
            book_id=book.id, student_id=f["student_id"],
            issue_date=parse_date(f.get("issue_date")) or date.today(),
            due_date=parse_date(f.get("due_date")),
        )
        book.available_copies -= 1
        db.session.add(issue)
        db.session.commit()
        flash("Book issued.", "success")
        return redirect(url_for("admin.book_issues_list"))
    return render_template("admin/book_issue_form.html", books=books, students=students)


@admin_bp.route("/library/issues/<int:issue_id>/return", methods=["POST"])
def book_issue_return(issue_id):
    issue = BookIssue.query.get_or_404(issue_id)
    if issue.return_date:
        flash("This book has already been returned.", "info")
        return redirect(url_for("admin.book_issues_list"))

    issue.return_date = date.today()
    fine = 0
    if issue.due_date and issue.return_date > issue.due_date:
        days_late = (issue.return_date - issue.due_date).days
        fine = days_late * 5  # ₹5 per day fine
    issue.fine_amount = fine
    issue.book.available_copies += 1
    db.session.commit()
    flash(f"Book returned. Fine: ₹{fine}." if fine else "Book returned. No fine.", "success")
    return redirect(url_for("admin.book_issues_list"))


# ---------------------------------------------------------------------------
# Transport Module
# ---------------------------------------------------------------------------


@admin_bp.route("/transport")
def buses_list():
    buses = Bus.query.all()
    return render_template("admin/buses_list.html", buses=buses)


@admin_bp.route("/transport/add", methods=["GET", "POST"])
def buses_add():
    if request.method == "POST":
        f = request.form
        photo_path = save_photo(request.files.get("driver_photo"), subfolder="drivers")
        bus = Bus(
            bus_number=f["bus_number"].strip(), route=f.get("route"),
            driver_name=f.get("driver_name"), driver_phone=f.get("driver_phone"),
            driver_photo=photo_path,
        )
        db.session.add(bus)
        db.session.commit()
        flash("Bus added.", "success")
        return redirect(url_for("admin.buses_list"))
    return render_template("admin/bus_form.html", bus=None)


@admin_bp.route("/transport/<int:bus_id>/edit", methods=["GET", "POST"])
def buses_edit(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    if request.method == "POST":
        f = request.form
        bus.bus_number = f["bus_number"].strip()
        bus.route = f.get("route")
        bus.driver_name = f.get("driver_name")
        bus.driver_phone = f.get("driver_phone")
        new_photo = save_photo(request.files.get("driver_photo"), subfolder="drivers")
        if new_photo:
            bus.driver_photo = new_photo
        db.session.commit()
        flash("Bus updated.", "success")
        return redirect(url_for("admin.buses_list"))
    return render_template("admin/bus_form.html", bus=bus)


@admin_bp.route("/transport/<int:bus_id>/delete", methods=["POST"])
def buses_delete(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    db.session.delete(bus)
    db.session.commit()
    flash("Bus deleted.", "info")
    return redirect(url_for("admin.buses_list"))


# ---------------------------------------------------------------------------
# Leave requests (approve / reject)
# ---------------------------------------------------------------------------


@admin_bp.route("/leave-requests")
def leave_requests_list():
    status = request.args.get("status", "Pending")
    query = LeaveRequest.query.join(Student)
    if status and status != "All":
        query = query.filter(LeaveRequest.status == status)
    requests_ = query.order_by(LeaveRequest.applied_at.desc()).all()
    return render_template("admin/leave_requests_list.html", requests=requests_, status=status)


@admin_bp.route("/leave-requests/<int:req_id>/decide", methods=["POST"])
def leave_requests_decide(req_id):
    leave = LeaveRequest.query.get_or_404(req_id)
    decision = request.form.get("decision")
    if decision in ("Approved", "Rejected"):
        leave.status = decision
        db.session.commit()
        flash(f"Leave request {decision.lower()}.", "success")
    return redirect(url_for("admin.leave_requests_list"))


# ---------------------------------------------------------------------------
# Reports (Student / Attendance / Fee / Marks / Assignment — CSV/Excel export)
# ---------------------------------------------------------------------------


@admin_bp.route("/reports")
def reports():
    return render_template("admin/reports.html")


@admin_bp.route("/reports/students.csv")
def report_students_csv():
    students = Student.query.join(User).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Name", "Email", "Phone", "Course", "Department", "Semester", "Status"])
    for s in students:
        writer.writerow([
            s.student_code, s.user.full_name, s.user.email, s.user.phone,
            s.course.name if s.course else "", s.department.name if s.department else "",
            s.semester, s.status,
        ])
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=student_report.csv"})


@admin_bp.route("/reports/attendance.csv")
def report_attendance_csv():
    records = Attendance.query.join(Student).order_by(Attendance.date).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Student", "Department", "Subject", "Status"])
    for r in records:
        writer.writerow([
            r.date, r.student.user.full_name,
            r.student.department.name if r.student.department else "", r.subject.name, r.status,
        ])
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})


@admin_bp.route("/reports/fees.csv")
def report_fees_csv():
    fees = Fee.query.join(Student).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student", "Fee Name", "Amount", "Paid", "Remaining", "Status"])
    for f in fees:
        writer.writerow([f.student.user.full_name, f.fee_name, f.amount, f.paid_amount, f.remaining,
                          "Paid" if f.is_paid else "Pending"])
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=fee_report.csv"})


@admin_bp.route("/reports/marks.csv")
def report_marks_csv():
    marks = Mark.query.join(Student).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student", "Subject", "Internal", "External", "Total", "Grade", "Result"])
    for m in marks:
        writer.writerow([m.student.user.full_name, m.subject.name, m.internal_marks, m.external_marks,
                          m.total, m.grade, m.result])
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=marks_report.csv"})


@admin_bp.route("/reports/assignments.csv")
def report_assignments_csv():
    assignments = Assignment.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Subject", "Due Date", "Submissions"])
    for a in assignments:
        writer.writerow([a.title, a.subject.name, a.due_date, len(a.submissions)])
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=assignment_report.csv"})


# ---------------------------------------------------------------------------
# Employee / HR Module
# ---------------------------------------------------------------------------


@admin_bp.route("/employees")
def employees_dashboard():
    total_employees = Employee.query.count()
    today = date.today()

    present_today_ids = {
        a.employee_id for a in EmployeeAttendance.query.filter_by(date=today, status="Present").all()
    }
    on_leave_ids = {
        a.employee_id for a in EmployeeAttendance.query.filter_by(date=today, status="Leave").all()
    }

    new_employees = Employee.query.filter(Employee.joining_date >= today - timedelta(days=30)).count()

    dept_counts = (
        db.session.query(Department.name, func.count(Employee.id))
        .outerjoin(Employee, Employee.department_id == Department.id)
        .group_by(Department.id)
        .all()
    )

    salary_total = db.session.query(func.coalesce(func.sum(Employee.salary), 0)).scalar() or 0

    notices = Notice.query.order_by(Notice.posted_at.desc()).limit(5).all()

    q = request.args.get("q", "").strip()
    department_id = request.args.get("department_id", type=int)
    designation = request.args.get("designation", "").strip()

    query = Employee.query.join(User)
    if q:
        like = f"%{q}%"
        query = query.filter((User.full_name.ilike(like)) | (Employee.employee_code.ilike(like)) | (User.email.ilike(like)))
    if department_id:
        query = query.filter(Employee.department_id == department_id)
    if designation:
        query = query.filter(Employee.designation == designation)
    employees = query.order_by(Employee.id.desc()).all()

    departments = Department.query.all()

    return render_template(
        "admin/employees_dashboard.html",
        total_employees=total_employees, present_today=len(present_today_ids),
        on_leave=len(on_leave_ids), new_employees=new_employees,
        dept_counts=dept_counts, salary_total=salary_total, notices=notices,
        employees=employees, departments=departments, designations=EMPLOYEE_DESIGNATIONS,
        q=q, department_id=department_id, designation=designation,
    )


@admin_bp.route("/employees/export")
def employees_export():
    employees = Employee.query.join(User).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee ID", "Name", "Email", "Phone", "Department", "Designation",
                      "Qualification", "Experience", "Joining Date", "Salary", "Type", "Status"])
    for e in employees:
        writer.writerow([
            e.employee_code, e.user.full_name, e.user.email, e.user.phone,
            e.department.name if e.department else "", e.designation, e.qualification,
            e.experience_years, e.joining_date, e.salary, e.employment_type, e.status,
        ])
    return Response(
        output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@admin_bp.route("/employees/add", methods=["GET", "POST"])
def employees_add():
    departments = Department.query.all()
    if request.method == "POST":
        f = request.form
        password = f.get("password") or "changeme123"
        confirm_password = f.get("confirm_password") or password
        if password != confirm_password:
            flash("Password and Confirm Password do not match.", "danger")
            return redirect(url_for("admin.employees_add"))

        photo_path = save_photo(request.files.get("photo"), subfolder="employees")

        user = User(
            full_name=f["full_name"].strip(),
            username=f["username"].strip(),
            email=f["email"].strip().lower(),
            phone=f.get("phone", "").strip(),
            dob=parse_date(f.get("dob")),
            gender=f.get("gender"),
            photo=photo_path,
            role="employee",
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        employee = Employee(
            user_id=user.id,
            department_id=f.get("department_id") or None,
            designation=f.get("designation"),
            qualification=f.get("qualification"),
            experience_years=f.get("experience_years") or 0,
            joining_date=parse_date(f.get("joining_date")) or date.today(),
            salary=f.get("salary") or 0,
            employment_type=f.get("employment_type", "Permanent"),
            status=f.get("status", "Active"),
            address=f.get("address"),
        )
        db.session.add(employee)
        db.session.flush()
        employee.employee_code = generate_code("EMP", employee.id)
        db.session.commit()
        flash(f"Employee {user.full_name} added successfully.", "success")
        return redirect(url_for("admin.employees_dashboard"))

    return render_template(
        "admin/employee_form.html", departments=departments, designations=EMPLOYEE_DESIGNATIONS,
        employment_types=EMPLOYMENT_TYPES, employee=None,
    )


@admin_bp.route("/employees/<int:employee_id>")
def employees_view(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    return render_template("admin/employee_view.html", employee=employee)


@admin_bp.route("/employees/<int:employee_id>/edit", methods=["GET", "POST"])
def employees_edit(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    departments = Department.query.all()
    if request.method == "POST":
        f = request.form
        employee.user.full_name = f["full_name"].strip()
        employee.user.email = f["email"].strip().lower()
        employee.user.phone = f.get("phone", "").strip()
        employee.user.dob = parse_date(f.get("dob"))
        employee.user.gender = f.get("gender")
        employee.department_id = f.get("department_id") or None
        employee.designation = f.get("designation")
        employee.qualification = f.get("qualification")
        employee.experience_years = f.get("experience_years") or 0
        employee.joining_date = parse_date(f.get("joining_date")) or employee.joining_date
        employee.salary = f.get("salary") or 0
        employee.employment_type = f.get("employment_type", "Permanent")
        employee.status = f.get("status", "Active")
        employee.address = f.get("address")
        new_photo = save_photo(request.files.get("photo"), subfolder="employees")
        if new_photo:
            employee.user.photo = new_photo
        db.session.commit()
        flash("Employee updated.", "success")
        return redirect(url_for("admin.employees_dashboard"))
    return render_template(
        "admin/employee_form.html", departments=departments, designations=EMPLOYEE_DESIGNATIONS,
        employment_types=EMPLOYMENT_TYPES, employee=employee,
    )


@admin_bp.route("/employees/<int:employee_id>/delete", methods=["POST"])
def employees_delete(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    user = employee.user
    db.session.delete(employee)
    db.session.delete(user)
    db.session.commit()
    flash("Employee deleted.", "info")
    return redirect(url_for("admin.employees_dashboard"))


# ---------------------------------------------------------------------------
# Employee attendance (check-in/out, daily status)
# ---------------------------------------------------------------------------


@admin_bp.route("/employees/attendance", methods=["GET", "POST"])
def employee_attendance_take():
    selected_date = request.values.get("date") or date.today().isoformat()
    att_date = parse_date(selected_date) or date.today()
    employees = Employee.query.join(User).filter(Employee.status == "Active").order_by(User.full_name).all()

    if request.method == "POST":
        for emp in employees:
            status = request.form.get(f"status_{emp.id}", "Present")
            check_in = request.form.get(f"checkin_{emp.id}")
            check_out = request.form.get(f"checkout_{emp.id}")
            existing = EmployeeAttendance.query.filter_by(employee_id=emp.id, date=att_date).first()
            check_in_t = datetime.strptime(check_in, "%H:%M").time() if check_in else None
            check_out_t = datetime.strptime(check_out, "%H:%M").time() if check_out else None
            if existing:
                existing.status = status
                existing.check_in = check_in_t
                existing.check_out = check_out_t
            else:
                db.session.add(EmployeeAttendance(
                    employee_id=emp.id, date=att_date, status=status,
                    check_in=check_in_t, check_out=check_out_t,
                ))
        db.session.commit()
        flash("Employee attendance saved.", "success")
        return redirect(url_for("admin.employee_attendance_take", date=selected_date))

    existing_map = {
        a.employee_id: a for a in EmployeeAttendance.query.filter_by(date=att_date).all()
    }
    return render_template(
        "admin/employee_attendance_take.html", employees=employees,
        selected_date=selected_date, existing_map=existing_map,
    )


@admin_bp.route("/employees/attendance/report")
def employee_attendance_report():
    month = request.args.get("month")
    query = EmployeeAttendance.query.join(Employee)
    if month:
        query = query.filter(func.strftime("%Y-%m", EmployeeAttendance.date) == month)
    records = query.order_by(EmployeeAttendance.date.desc()).limit(500).all()
    return render_template("admin/employee_attendance_report.html", records=records, month=month)


@admin_bp.route("/employees/attendance/export")
def employee_attendance_export():
    month = request.args.get("month")
    query = EmployeeAttendance.query.join(Employee)
    if month:
        query = query.filter(func.strftime("%Y-%m", EmployeeAttendance.date) == month)
    records = query.order_by(EmployeeAttendance.date).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Employee", "Status", "Check In", "Check Out"])
    for r in records:
        writer.writerow([r.date, r.employee.user.full_name, r.status, r.check_in or "", r.check_out or ""])
    label = month or "all"
    return Response(output.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": f"attachment; filename=employee_attendance_{label}.csv"})


# ---------------------------------------------------------------------------
# Employee leave (admin records + approves/rejects)
# ---------------------------------------------------------------------------


@admin_bp.route("/employees/leave")
def employee_leave_list():
    status = request.args.get("status", "Pending")
    query = EmployeeLeaveRequest.query.join(Employee)
    if status and status != "All":
        query = query.filter(EmployeeLeaveRequest.status == status)
    requests_ = query.order_by(EmployeeLeaveRequest.applied_at.desc()).all()
    return render_template("admin/employee_leave_list.html", requests=requests_, status=status)


@admin_bp.route("/employees/leave/add", methods=["GET", "POST"])
def employee_leave_add():
    employees = Employee.query.join(User).all()
    if request.method == "POST":
        f = request.form
        db.session.add(EmployeeLeaveRequest(
            employee_id=f["employee_id"],
            reason=f["reason"].strip(),
            from_date=parse_date(f["from_date"]),
            to_date=parse_date(f["to_date"]),
        ))
        db.session.commit()
        flash("Leave request recorded.", "success")
        return redirect(url_for("admin.employee_leave_list"))
    return render_template("admin/employee_leave_form.html", employees=employees)


@admin_bp.route("/employees/leave/<int:req_id>/decide", methods=["POST"])
def employee_leave_decide(req_id):
    leave = EmployeeLeaveRequest.query.get_or_404(req_id)
    decision = request.form.get("decision")
    if decision in ("Approved", "Rejected"):
        leave.status = decision
        db.session.commit()
        flash(f"Leave request {decision.lower()}.", "success")
    return redirect(url_for("admin.employee_leave_list"))


@admin_bp.route("/employees/leave/<int:req_id>/cancel", methods=["POST"])
def employee_leave_cancel(req_id):
    leave = EmployeeLeaveRequest.query.get_or_404(req_id)
    if leave.status == "Pending":
        db.session.delete(leave)
        db.session.commit()
        flash("Leave request cancelled.", "info")
    else:
        flash("Only pending leave requests can be cancelled.", "danger")
    return redirect(url_for("admin.employee_leave_list"))


