from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
)

from app.models.concern import Category, ConcernStatus, Urgency
from app.models.user import Role


class LoginForm(FlaskForm):
    """User authentication form."""

    email = StringField(
        "Email Address",
        validators=[DataRequired(), Email(), Length(max=120)],
        render_kw={"placeholder": "e.g. student@campus.edu"},
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired()],
        render_kw={"placeholder": "Enter your password"},
    )
    submit = SubmitField("Sign In")


class RegisterForm(FlaskForm):
    """Student registration form."""

    name = StringField(
        "Full Name",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "e.g. Alex Rivera"},
    )
    email = StringField(
        "University Email",
        validators=[DataRequired(), Email(), Length(max=120)],
        render_kw={"placeholder": "e.g. alex.rivera@campus.edu"},
    )
    department = StringField(
        "Program / Department",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Computer Science, Batch 2026"},
    )
    phone = StringField(
        "Phone / Mobile",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "+1 (555) 019-2834"},
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=6, max=60)],
        render_kw={"placeholder": "At least 6 characters"},
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
        render_kw={"placeholder": "Repeat password"},
    )
    submit = SubmitField("Create Student Account")


class ConcernForm(FlaskForm):
    """Student concern submission form."""

    category = SelectField(
        "Concern Category",
        choices=[
            (Category.ACADEMIC, "Academic Matters"),
            (Category.EXAMINATION, "Examination & Results"),
            (Category.MESS, "Mess & Dining Services"),
            (Category.RESIDENTIAL, "Hostel & Residential"),
            (Category.WELLBEING, "Wellbeing & Mental Health (Confidential)"),
            (Category.MAINTENANCE, "Maintenance / Housekeeping (External Link)"),
            (Category.OTHER, "Other Campus Concern"),
        ],
        validators=[DataRequired()],
    )
    urgency = SelectField(
        "Urgency Level",
        choices=[
            (Urgency.LOW, "Low - General inquiry"),
            (Urgency.MEDIUM, "Medium - Requires attention within 2-3 days"),
            (Urgency.HIGH, "High - Time-sensitive matter"),
            (Urgency.URGENT, "Urgent - Critical / Immediate action required"),
        ],
        default=Urgency.MEDIUM,
        validators=[DataRequired()],
    )
    title = StringField(
        "Summary Title",
        validators=[DataRequired(), Length(min=5, max=150)],
        render_kw={"placeholder": "Brief description of the issue"},
    )
    description = TextAreaField(
        "Detailed Description",
        validators=[DataRequired(), Length(min=10, max=3000)],
        render_kw={
            "rows": 6,
            "placeholder": "Provide full context, dates, courses, or hostel room details as relevant...",
        },
    )
    submit = SubmitField("Submit Concern")


class CommentForm(FlaskForm):
    """Concern comment form."""

    message = TextAreaField(
        "Add a Message / Comment",
        validators=[DataRequired(), Length(min=2, max=1500)],
        render_kw={"rows": 3, "placeholder": "Type your message or update here..."},
    )
    submit = SubmitField("Post Comment")


class StatusUpdateForm(FlaskForm):
    """Staff status update form."""

    status = SelectField(
        "New Status",
        choices=[
            (ConcernStatus.ACKNOWLEDGED, "Acknowledge Concern"),
            (ConcernStatus.IN_PROGRESS, "Mark In Progress"),
            (ConcernStatus.RESOLVED, "Mark Resolved"),
            (ConcernStatus.CLOSED, "Close Concern"),
        ],
        validators=[DataRequired()],
    )
    comment = TextAreaField(
        "Update Note (Visible to Student)",
        validators=[Optional(), Length(max=1000)],
        render_kw={"rows": 3, "placeholder": "Explain the status transition or action taken..."},
    )
    submit = SubmitField("Update Status")


class EscalationForm(FlaskForm):
    """Staff escalation form."""

    reason = TextAreaField(
        "Escalation Reason",
        validators=[DataRequired(), Length(min=5, max=1000)],
        render_kw={
            "rows": 3,
            "placeholder": "Explain why this concern requires higher-level intervention...",
        },
    )
    submit = SubmitField("Escalate Concern")


class AvailabilitySlotForm(FlaskForm):
    """Staff publishing availability slot."""

    slot_date = DateField("Date", validators=[DataRequired()])
    start_time = TimeField("Start Time", validators=[DataRequired()])
    end_time = TimeField("End Time", validators=[DataRequired()])
    location = StringField(
        "Cabin / Office Location",
        validators=[DataRequired(), Length(max=120)],
        render_kw={"placeholder": "e.g. Cabin 204, Academic Block A"},
    )
    notes = StringField(
        "Notes / Instructions (Optional)",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "e.g. Bring syllabus or course registration slip"},
    )
    submit = SubmitField("Publish Availability Slot")


class AppointmentRequestForm(FlaskForm):
    """Student appointment booking form."""

    staff_id = SelectField("Staff Contact", coerce=int, validators=[DataRequired()])
    slot_id = SelectField("Available Slot", coerce=int, validators=[Optional()])
    concern_id = SelectField(
        "Related Concern (Optional)", coerce=int, validators=[Optional()]
    )
    purpose = TextAreaField(
        "Purpose of Appointment",
        validators=[DataRequired(), Length(min=5, max=500)],
        render_kw={
            "rows": 3,
            "placeholder": "Briefly state what you wish to discuss...",
        },
    )
    submit = SubmitField("Submit Appointment Request")


class AppointmentActionForm(FlaskForm):
    """Staff appointment response form (Approve, Decline, Reschedule)."""

    action = SelectField(
        "Action",
        choices=[
            ("Approved", "Approve Request"),
            ("Declined", "Decline Request"),
            ("Rescheduled", "Reschedule / Propose New Time"),
            ("Completed", "Mark Completed"),
        ],
        validators=[DataRequired()],
    )
    notes = TextAreaField(
        "Staff Notes / Feedback",
        validators=[Optional(), Length(max=500)],
        render_kw={"rows": 2, "placeholder": "Add note for the student..."},
    )
    reschedule_date = DateField("New Date", validators=[Optional()])
    reschedule_start_time = TimeField("New Start Time", validators=[Optional()])
    reschedule_end_time = TimeField("New End Time", validators=[Optional()])
    reschedule_location = StringField(
        "Meeting Location", validators=[Optional(), Length(max=120)]
    )
    submit = SubmitField("Update Appointment")


class RoutingRuleForm(FlaskForm):
    """Admin routing table entry form."""

    category = StringField(
        "Concern Category",
        validators=[DataRequired(), Length(max=50)],
        render_kw={"placeholder": "e.g. Academic"},
    )
    target_role = SelectField(
        "Target Role",
        choices=[(r, r) for r in Role.STAFF_ROLES],
        validators=[DataRequired()],
    )
    description = StringField(
        "Description",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "Primary routing for this concern category"},
    )
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Routing Rule")


class EscalationRuleForm(FlaskForm):
    """Admin escalation rule form."""

    category = SelectField(
        "Category (Optional)",
        choices=[("", "Any Category / Global")]
        + [(c, c) for c in Category.SUBMITTABLE_CATEGORIES],
        validators=[Optional()],
    )
    current_role = SelectField(
        "Current Role",
        choices=[(r, r) for r in Role.STAFF_ROLES],
        validators=[DataRequired()],
    )
    next_role = SelectField(
        "Escalate To Next Role",
        choices=[(r, r) for r in Role.STAFF_ROLES],
        validators=[DataRequired()],
    )
    order_level = IntegerField(
        "Order Level",
        default=1,
        validators=[DataRequired(), NumberRange(min=1, max=10)],
    )
    description = StringField(
        "Description",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "e.g. Mentor escalates to Program Coordinator"},
    )
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Escalation Rule")


class UserEditForm(FlaskForm):
    """Admin user edit form."""

    name = StringField("Full Name", validators=[DataRequired(), Length(max=100)])
    role = SelectField(
        "Role",
        choices=[(r, r) for r in Role.ALL_ROLES],
        validators=[DataRequired()],
    )
    department = StringField("Department", validators=[Optional(), Length(max=100)])
    cabin_location = StringField("Office / Cabin Location", validators=[Optional(), Length(max=100)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    is_active = BooleanField("Account Active", default=True)
    submit = SubmitField("Update User")


class SystemSettingsForm(FlaskForm):
    """Admin system configuration form."""

    overdue_threshold_hours = IntegerField(
        "Overdue Threshold (Hours)",
        validators=[DataRequired(), NumberRange(min=1, max=720)],
        description="Hours unacknowledged before a concern is flagged overdue.",
    )
    maintenance_portal_url = StringField(
        "External Maintenance Portal URL",
        validators=[DataRequired(), Length(max=255)],
        description="Redirect target for maintenance and housekeeping concerns.",
    )
    campus_name = StringField(
        "Campus / Institution Name",
        validators=[DataRequired(), Length(max=100)],
    )
    submit = SubmitField("Save Settings")
