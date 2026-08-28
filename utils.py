import os
import uuid
from datetime import datetime
from functools import wraps

from flask import current_app, abort
from flask_login import current_user
from werkzeug.utils import secure_filename


def parse_date(value):
    """Convert an HTML date-input string ('YYYY-MM-DD') to a Python date, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def save_photo(file_storage, subfolder="profiles"):
    """Save an uploaded image and return its relative path (under static/), or None."""
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in current_app.config["ALLOWED_IMAGE_EXT"]:
        return None
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return f"uploads/{subfolder}/{filename}"


def save_document(file_storage, subfolder="assignments"):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in current_app.config["ALLOWED_DOC_EXT"]:
        return None
    filename = f"{uuid.uuid4().hex}_{secure_filename(file_storage.filename)}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, filename))
    return f"uploads/{subfolder}/{filename}"


def generate_code(prefix, number):
    return f"{prefix}{number:04d}"


def roles_required(*roles):
    """Restrict a view to the given user roles."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def is_hod_of_department(department_id):
    """True if the current user is the HOD teacher assigned to this department."""
    if not current_user.is_authenticated or current_user.role != "teacher":
        return False
    teacher = current_user.teacher_profile
    return bool(teacher and teacher.designation == "HOD" and teacher.department_id == department_id)


def can_manage_department(department_id):
    """Only the admin or that department's own HOD may edit its microsite content."""
    if not current_user.is_authenticated:
        return False
    if current_user.role == "admin":
        return True
    return is_hod_of_department(department_id)


def department_manage_required(view_func):
    """Restrict a view to admin or the relevant department's HOD (dept_id/department_id kwarg)."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        dept_id = kwargs.get("dept_id") or kwargs.get("department_id")
        if not can_manage_department(dept_id):
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped
