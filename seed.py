"""
Database seeding script for the Campus Student Support and Concern Portal.
Populates realistic demo users for all university roles, database routing rules,
configurable escalation chains, published availability slots, and sample concerns.
"""

from datetime import date, datetime, time, timedelta, timezone

from app import create_app
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

from app.models.appointment import Appointment, AppointmentStatus, AvailabilitySlot
from app.models.concern import (
    Category,
    Concern,
    ConcernComment,
    ConcernStatus,
    ConcernTimeline,
    Urgency,
)
from app.models.notification import Notification
from app.models.routing import EscalationRule, RoutingRule, SystemSetting
from app.models.user import Role, User


def seed_database():
    app = create_app("development")
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        print("Seeding System Settings...")
        SystemSetting.set_value(
            "overdue_threshold_hours",
            "24",
            "Hours unacknowledged before flagged overdue",
        )
        SystemSetting.set_value(
            "maintenance_portal_url",
            "https://maintenance.campus.edu",
            "External facilities maintenance link",
        )
        SystemSetting.set_value(
            "campus_name",
            "Central University Campus",
            "Campus institution display name",
        )

        print("Seeding Users for all roles...")
        demo_password = "Password123!"

        users_data = [
            {
                "name": "Alex Rivera",
                "email": "student@campus.edu",
                "role": Role.STUDENT,
                "department": "Computer Science, Batch 2026",
                "phone": "+1 (555) 019-2831",
                "cabin_location": "Hostel 3, Room 412",
            },
            {
                "name": "Jordan Lee",
                "email": "student2@campus.edu",
                "role": Role.STUDENT,
                "department": "Mechanical Engineering, Batch 2025",
                "phone": "+1 (555) 019-2832",
                "cabin_location": "Hostel 1, Room 105",
            },
            {
                "name": "Dr. Sarah Vance",
                "email": "mentor@campus.edu",
                "role": Role.MENTOR,
                "department": "School of Computing",
                "phone": "+1 (555) 019-4401",
                "cabin_location": "Cabin 204, Academic Block A",
            },
            {
                "name": "Prof. Alan Turing",
                "email": "coordinator@campus.edu",
                "role": Role.PROGRAM_COORDINATOR,
                "department": "Academic Programs Directorate",
                "phone": "+1 (555) 019-4402",
                "cabin_location": "Cabin 305, Engineering Wing",
            },
            {
                "name": "Col. James Wilson",
                "email": "warden@campus.edu",
                "role": Role.WARDEN,
                "department": "Hostel Administration",
                "phone": "+1 (555) 019-4403",
                "cabin_location": "Hostel Block A Office",
            },
            {
                "name": "Prof. Marcus Brody",
                "email": "headwarden@campus.edu",
                "role": Role.HEAD_WARDEN,
                "department": "Chief Warden Directorate",
                "phone": "+1 (555) 019-4404",
                "cabin_location": "Central Hostel Office, Room 12",
            },
            {
                "name": "Dean Robert Hayes",
                "email": "dean_sa@campus.edu",
                "role": Role.DEAN_STUDENT_AFFAIRS,
                "department": "Deanery of Student Affairs",
                "phone": "+1 (555) 019-4405",
                "cabin_location": "Student Affairs Complex, Suite 101",
            },
            {
                "name": "Dean Eleanor Roosevelt",
                "email": "dean@campus.edu",
                "role": Role.DEAN,
                "department": "Office of University Dean",
                "phone": "+1 (555) 019-4406",
                "cabin_location": "Vice Chancellor Building, 2nd Floor",
            },
            {
                "name": "Dr. Grace Hopper",
                "email": "wellbeing@campus.edu",
                "role": Role.WELLBEING_STAFF,
                "department": "Campus Counseling & Health Center",
                "phone": "+1 (555) 019-4407",
                "cabin_location": "Health Center, Counseling Room 3",
            },
            {
                "name": "System Administrator",
                "email": "admin@campus.edu",
                "role": Role.ADMIN,
                "department": "Campus IT Systems",
                "phone": "+1 (555) 019-4408",
                "cabin_location": "IT Operations Center",
            },
        ]

        users = {}
        for udata in users_data:
            user = User(
                name=udata["name"],
                email=udata["email"],
                role=udata["role"],
                department=udata["department"],
                phone=udata["phone"],
                cabin_location=udata["cabin_location"],
                is_active=True,
            )
            user.set_password(demo_password)
            db.session.add(user)
            users[udata["email"]] = user

        db.session.commit()

        print("Seeding Database Routing Rules...")
        routing_rules = [
            RoutingRule(
                category=Category.ACADEMIC,
                target_role=Role.MENTOR,
                description="Course registration, syllabus coverage, and academic guidance.",
            ),
            RoutingRule(
                category=Category.EXAMINATION,
                target_role=Role.PROGRAM_COORDINATOR,
                description="Mid-term/final exams, grading questions, and transcript verification.",
            ),
            RoutingRule(
                category=Category.MESS,
                target_role=Role.WARDEN,
                description="Dining hall hygiene, mess menu, meal quality, and timing issues.",
            ),
            RoutingRule(
                category=Category.RESIDENTIAL,
                target_role=Role.WARDEN,
                description="Hostel room allocation, noise disruption, and residential conduct.",
            ),
            RoutingRule(
                category=Category.WELLBEING,
                target_role=Role.WELLBEING_STAFF,
                description="Confidential mental health, stress, wellness, and medical support.",
            ),
            RoutingRule(
                category=Category.OTHER,
                target_role=Role.DEAN_STUDENT_AFFAIRS,
                description="General student grievances and inter-departmental matters.",
            ),
        ]
        db.session.add_all(routing_rules)

        print("Seeding Configurable Escalation Rules...")
        escalation_rules = [
            # Academic hierarchy: Mentor -> Program Coordinator -> Dean
            EscalationRule(
                current_role=Role.MENTOR,
                next_role=Role.PROGRAM_COORDINATOR,
                category=Category.ACADEMIC,
                order_level=1,
                description="Mentor escalates complex academic cases to Program Coordinator.",
            ),
            EscalationRule(
                current_role=Role.PROGRAM_COORDINATOR,
                next_role=Role.DEAN,
                category=None,
                order_level=2,
                description="Program Coordinator escalates to Dean.",
            ),
            # Residential & Mess hierarchy: Warden -> Head Warden -> Dean SA -> Dean
            EscalationRule(
                current_role=Role.WARDEN,
                next_role=Role.HEAD_WARDEN,
                category=None,
                order_level=1,
                description="Warden escalates to Head Warden.",
            ),
            EscalationRule(
                current_role=Role.HEAD_WARDEN,
                next_role=Role.DEAN_STUDENT_AFFAIRS,
                category=None,
                order_level=2,
                description="Head Warden escalates to Dean of Student Affairs.",
            ),
            EscalationRule(
                current_role=Role.DEAN_STUDENT_AFFAIRS,
                next_role=Role.DEAN,
                category=None,
                order_level=3,
                description="Dean of Student Affairs escalates to Dean.",
            ),
            # Wellbeing escalation if medical escalation needed
            EscalationRule(
                current_role=Role.WELLBEING_STAFF,
                next_role=Role.DEAN_STUDENT_AFFAIRS,
                category=Category.WELLBEING,
                order_level=1,
                description="Confidential wellbeing escalation to Dean SA.",
            ),
        ]
        db.session.add_all(escalation_rules)
        db.session.commit()

        print("Seeding Staff Availability Slots...")
        today = date.today()
        slots_data = [
            # Mentor slots
            AvailabilitySlot(
                staff_id=users["mentor@campus.edu"].id,
                date=today + timedelta(days=1),
                start_time=time(10, 0),
                end_time=time(11, 30),
                location="Cabin 204, Academic Block A",
                notes="Bring syllabus or course registration questions.",
                is_available=True,
            ),
            AvailabilitySlot(
                staff_id=users["mentor@campus.edu"].id,
                date=today + timedelta(days=2),
                start_time=time(14, 0),
                end_time=time(15, 30),
                location="Cabin 204, Academic Block A",
                notes="Afternoon advising hour.",
                is_available=True,
            ),
            # Program Coordinator slots
            AvailabilitySlot(
                staff_id=users["coordinator@campus.edu"].id,
                date=today + timedelta(days=2),
                start_time=time(11, 0),
                end_time=time(12, 30),
                location="Cabin 305, Engineering Wing",
                notes="Exam re-evaluation and curriculum advisory.",
                is_available=True,
            ),
            # Warden slots
            AvailabilitySlot(
                staff_id=users["warden@campus.edu"].id,
                date=today + timedelta(days=1),
                start_time=time(17, 0),
                end_time=time(18, 30),
                location="Hostel Block A Office",
                notes="Mess feedback and room change consultation.",
                is_available=True,
            ),
            # Wellbeing Staff slots
            AvailabilitySlot(
                staff_id=users["wellbeing@campus.edu"].id,
                date=today + timedelta(days=1),
                start_time=time(15, 0),
                end_time=time(16, 0),
                location="Health Center, Counseling Room 3",
                notes="Confidential 1-on-1 wellness check-in.",
                is_available=True,
            ),
        ]
        db.session.add_all(slots_data)
        db.session.commit()

        print("Seeding Sample Concerns and Timelines...")
        student_user = users["student@campus.edu"]

        # Concern 1: Academic (In Progress)
        c1 = Concern(
            tracking_number="CC-2026-1011",
            student_id=student_user.id,
            category=Category.ACADEMIC,
            title="Clash in Final Semester Elective Schedule",
            description="Two of my core elective courses (Advanced Distributed Systems and Machine Learning) are scheduled at the exact same lecture slot on Tuesdays and Thursdays.",
            urgency=Urgency.HIGH,
            status=ConcernStatus.IN_PROGRESS,
            assigned_role=Role.MENTOR,
            assigned_to_user_id=users["mentor@campus.edu"].id,
            is_confidential=False,
            created_at=utc_now() - timedelta(hours=18),
            acknowledged_at=utc_now() - timedelta(hours=14),
        )
        db.session.add(c1)
        db.session.flush()

        t1_1 = ConcernTimeline(
            concern_id=c1.id,
            action="Concern Submitted",
            details="Concern submitted and auto-routed to Mentor.",
            performed_by_id=student_user.id,
            created_at=utc_now() - timedelta(hours=18),
        )
        t1_2 = ConcernTimeline(
            concern_id=c1.id,
            action="Status changed to Acknowledged",
            details="Dr. Sarah Vance acknowledged the elective clash issue.",
            performed_by_id=users["mentor@campus.edu"].id,
            created_at=utc_now() - timedelta(hours=14),
        )
        t1_3 = ConcernTimeline(
            concern_id=c1.id,
            action="Status changed to In Progress",
            details="Reviewing alternate section timings with timetable coordinator.",
            performed_by_id=users["mentor@campus.edu"].id,
            created_at=utc_now() - timedelta(hours=8),
        )
        com1 = ConcernComment(
            concern_id=c1.id,
            author_id=users["mentor@campus.edu"].id,
            message="Hello Alex, I have consulted with the department scheduler. An alternate section for Machine Learning is opening tomorrow.",
            is_internal=False,
            created_at=utc_now() - timedelta(hours=7),
        )
        db.session.add_all([t1_1, t1_2, t1_3, com1])

        # Concern 2: Mess (Acknowledged)
        c2 = Concern(
            tracking_number="CC-2026-1022",
            student_id=student_user.id,
            category=Category.MESS,
            title="Mess Food Quality and Dinner Timing in Hostel 3",
            description="Dinner service runs out of vegetarian meal items past 8:45 PM even though mess timings are until 9:30 PM.",
            urgency=Urgency.MEDIUM,
            status=ConcernStatus.ACKNOWLEDGED,
            assigned_role=Role.WARDEN,
            assigned_to_user_id=users["warden@campus.edu"].id,
            is_confidential=False,
            created_at=utc_now() - timedelta(hours=10),
            acknowledged_at=utc_now() - timedelta(hours=4),
        )
        db.session.add(c2)
        db.session.flush()

        t2_1 = ConcernTimeline(
            concern_id=c2.id,
            action="Concern Submitted",
            details="Concern submitted and auto-routed to Warden.",
            performed_by_id=student_user.id,
            created_at=utc_now() - timedelta(hours=10),
        )
        t2_2 = ConcernTimeline(
            concern_id=c2.id,
            action="Status changed to Acknowledged",
            details="Col. James Wilson verified dinner shortage reports.",
            performed_by_id=users["warden@campus.edu"].id,
            created_at=utc_now() - timedelta(hours=4),
        )
        db.session.add_all([t2_1, t2_2])

        # Concern 3: Residential (Escalated to Head Warden)
        c3 = Concern(
            tracking_number="CC-2026-1033",
            student_id=student_user.id,
            category=Category.RESIDENTIAL,
            title="Persistent Night-time Noise Disruption in Hostel Wing B",
            description="Excessive speaker noise after midnight continues despite initial verbal notices issued by floor proctors.",
            urgency=Urgency.HIGH,
            status=ConcernStatus.ESCALATED,
            assigned_role=Role.HEAD_WARDEN,
            assigned_to_user_id=users["headwarden@campus.edu"].id,
            is_confidential=False,
            created_at=utc_now() - timedelta(hours=28),
            acknowledged_at=utc_now() - timedelta(hours=25),
        )
        db.session.add(c3)
        db.session.flush()

        t3_1 = ConcernTimeline(
            concern_id=c3.id,
            action="Concern Submitted",
            details="Auto-routed to Warden.",
            performed_by_id=student_user.id,
            created_at=utc_now() - timedelta(hours=28),
        )
        t3_2 = ConcernTimeline(
            concern_id=c3.id,
            action="Escalated to Head Warden",
            details="Escalated from Warden to Head Warden. Reason: Disciplinary action across multiple wings requires chief warden sanction.",
            performed_by_id=users["warden@campus.edu"].id,
            created_at=utc_now() - timedelta(hours=12),
        )
        com3 = ConcernComment(
            concern_id=c3.id,
            author_id=users["warden@campus.edu"].id,
            message="[Escalation Note] Escalated to Head Warden: Disciplinary action across multiple wings requires chief warden sanction.",
            is_internal=False,
            created_at=utc_now() - timedelta(hours=12),
        )
        db.session.add_all([t3_1, t3_2, com3])

        # Concern 4: CONFIDENTIAL Wellbeing Concern
        c4 = Concern(
            tracking_number="CC-2026-1044",
            student_id=student_user.id,
            category=Category.WELLBEING,
            title="Confidential Academic Stress & Anxiety Support Request",
            description="Experiencing high anxiety, insomnia, and exam fatigue ahead of project defense. Seeking confidential counseling session.",
            urgency=Urgency.HIGH,
            status=ConcernStatus.IN_PROGRESS,
            assigned_role=Role.WELLBEING_STAFF,
            assigned_to_user_id=users["wellbeing@campus.edu"].id,
            is_confidential=True,  # STRICTLY RESTRICTED TO STUDENT AND WELLBEING STAFF
            created_at=utc_now() - timedelta(hours=6),
            acknowledged_at=utc_now() - timedelta(hours=5),
        )
        db.session.add(c4)
        db.session.flush()

        t4_1 = ConcernTimeline(
            concern_id=c4.id,
            action="Concern Submitted",
            details="Confidential wellbeing route activated. Auto-routed strictly to Wellbeing Staff.",
            performed_by_id=student_user.id,
            created_at=utc_now() - timedelta(hours=6),
        )
        com4 = ConcernComment(
            concern_id=c4.id,
            author_id=users["wellbeing@campus.edu"].id,
            message="Hello Alex, I've reviewed your request with full confidentiality. Let's meet at Counseling Room 3 tomorrow afternoon.",
            is_internal=False,
            created_at=utc_now() - timedelta(hours=4),
        )
        db.session.add_all([t4_1, com4])

        # Concern 5: Overdue Unacknowledged Concern (>24 hours unacknowledged)
        c5 = Concern(
            tracking_number="CC-2026-1055",
            student_id=student_user.id,
            category=Category.EXAMINATION,
            title="Delayed Re-evaluation Grade Update for Discrete Mathematics",
            description="Application for re-evaluation was submitted 3 weeks ago, but portal still lists the old grade.",
            urgency=Urgency.URGENT,
            status=ConcernStatus.SUBMITTED,  # UNACKNOWLEDGED past 24h
            assigned_role=Role.PROGRAM_COORDINATOR,
            assigned_to_user_id=users["coordinator@campus.edu"].id,
            is_confidential=False,
            created_at=utc_now() - timedelta(hours=30),  # 30 hours old -> Overdue!
        )
        db.session.add(c5)
        db.session.flush()

        t5_1 = ConcernTimeline(
            concern_id=c5.id,
            action="Concern Submitted",
            details="Auto-routed to Program Coordinator.",
            performed_by_id=student_user.id,
            created_at=utc_now() - timedelta(hours=30),
        )
        db.session.add(t5_1)

        print("Seeding Sample Appointments...")
        appt1 = Appointment(
            student_id=student_user.id,
            staff_id=users["mentor@campus.edu"].id,
            slot_id=slots_data[0].id,
            concern_id=c1.id,
            purpose="Discuss elective clash resolution and credit adjustment.",
            status=AppointmentStatus.APPROVED,
            staff_notes="Approved. See you tomorrow at 10 AM in Cabin 204.",
        )
        slots_data[0].is_available = False

        appt2 = Appointment(
            student_id=student_user.id,
            staff_id=users["wellbeing@campus.edu"].id,
            slot_id=slots_data[4].id,
            concern_id=c4.id,
            purpose="Confidential wellness check-in.",
            status=AppointmentStatus.REQUESTED,
            staff_notes=None,
        )
        slots_data[4].is_available = False

        db.session.add_all([appt1, appt2])

        print("Seeding Initial Notifications...")
        n1 = Notification(
            user_id=student_user.id,
            title="Appointment Approved",
            message="Dr. Sarah Vance approved your appointment for tomorrow 10:00 AM.",
            link="/student/appointments",
            is_read=False,
        )
        n2 = Notification(
            user_id=student_user.id,
            title="Status Update on CC-2026-1011",
            message="Your concern is now In Progress.",
            link=f"/student/concerns/{c1.id}",
            is_read=True,
        )
        db.session.add_all([n1, n2])

        db.session.commit()
        print("Database seeded successfully with all roles, rules, and demo data!")


if __name__ == "__main__":
    seed_database()
