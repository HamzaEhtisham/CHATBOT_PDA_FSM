from flask import Flask, render_template, request, jsonify, session
from fsm import FSM
from pda import PDA
import json
import random
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = "chatbot_secret_key_2025"

# -------------------
# Helper Functions
# -------------------
# ---------- Dark UI Theme ----------
HEADER_BG = "#0f172a"        # Dark navy
HEADER_TEXT = "#22c55e"      # Neon green
ROW_BG_1 = "#020617"         # Dark background
ROW_BG_2 = "#020617cc"       # Alternate row
BORDER_COLOR = "#1e293b"     # Soft border
TEXT_COLOR = "#e5e7eb"       # Main text
SUBTEXT_COLOR = "#94a3b8"    # Muted text


def get_fsm_from_session():
    """Retrieve FSM from session or create a new one."""
    fsm = FSM()
    fsm.state = session.get('fsm_state', 'START')
    return fsm

def save_fsm_to_session(fsm):
    """Save FSM state to session."""
    session['fsm_state'] = fsm.state

def get_pda_from_session():
    """Retrieve PDA from session or create a new one."""
    pda = PDA()
    pda.stack = session.get('pda_stack', [])
    pda.history = session.get('pda_history', [])
    return pda

def save_pda_to_session(pda):
    """Save PDA state to session."""
    session['pda_stack'] = pda.stack
    session['pda_history'] = pda.history

# -------------------
# Data Extraction Functions
# -------------------

def extract_semester_number(text):
    """Extract semester number from text using regex."""
    patterns = [
        r'\bsem(?:ester)?\s*(\d+)',
        r'\b(\d+)(?:st|nd|rd|th)?\s*sem',
        r'\b(one|two|three|four|five|six|seven|eight|1|2|3|4|5|6|7|8)\b'
    ]
    
    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            sem_str = match.group(1)
            word_to_num = {
                'one': '1', 'two': '2', 'three': '3', 'four': '4',
                'five': '5', 'six': '6', 'seven': '7', 'eight': '8'
            }
            return word_to_num.get(sem_str, sem_str)
    return None

def extract_faculty_name(text):
    """Safely extract faculty name from user input."""
    text_lower = text.lower()
    # Remove common prefixes/titles
    prefixes = ["sir ", "miss ", "mr ", "ms ", "dr ", "prof "]
    for prefix in prefixes:
        text_lower = text_lower.replace(prefix, "")
    # Remove common phrases
    phrases = ["about", "tell me", "who is"]
    for ph in phrases:
        text_lower = text_lower.replace(ph, "")
    text_clean = text_lower.strip()
    # 1. Exact match
    for faculty_key in DATA["FACULTY"].keys():
        if text_clean == faculty_key:
            return faculty_key
    # 2. Partial match
    for faculty_key in DATA["FACULTY"].keys():
        if text_clean in faculty_key:
            return faculty_key
    # 3. Last name match (unique)
    potential_matches = []
    for faculty_key in DATA["FACULTY"].keys():
        last_name = faculty_key.split()[-1] if " " in faculty_key else faculty_key
        if last_name == text_clean:
            potential_matches.append(faculty_key)
    if len(potential_matches) == 1:
        return potential_matches[0]
    return None

def extract_event_name(text):
    """Extract specific event name from user input."""
    text_lower = text.lower()
    for event in DATA["EVENTS"]:
        if event["name"].lower() in text_lower:
            return event
    return None

def extract_course_code(text):
    """Extract course code from user input."""
    text_upper = text.upper()
    for course_code in DATA["COURSE_TO_FACULTY"].keys():
        if course_code in text_upper:
            return course_code
    # Check course names
    for sem_courses in DATA["COURSES"].values():
        for course in sem_courses:
            if course['name'].lower() in text.lower():
                return course['code']
    return None

# -------------------
# NEW: Prerequisites & Calendar Functions
# -------------------

def get_course_prerequisites(course_code):
    """Get prerequisites for a specific course."""
    if course_code in DATA["PREREQUISITES"]:
        prereqs = DATA["PREREQUISITES"][course_code]
        
        # Get course name
        course_name = None
        for sem_courses in DATA["COURSES"].values():
            for course in sem_courses:
                if course['code'] == course_code:
                    course_name = course['name']
                    break
            if course_name:
                break
        
        if not prereqs:
            return f"📚 <strong>{course_code}</strong>: {course_name}<br><br>✅ <strong>No prerequisites required!</strong><br>This is a foundational course you can take anytime."
        
        response = f"📚 <strong>{course_code}</strong>: {course_name}<br><br>"
        response += f"📋 <strong>Prerequisites Required:</strong><br><br>"
        
        for prereq_code in prereqs:
            prereq_name = None
            for sem_courses in DATA["COURSES"].values():
                for course in sem_courses:
                    if course['code'] == prereq_code:
                        prereq_name = course['name']
                        break
                if prereq_name:
                    break
            
            if prereq_name:
                response += f"• <strong>{prereq_code}</strong>: {prereq_name}<br>"
            else:
                response += f"• <strong>{prereq_code}</strong><br>"
        
        response += f"<br>⚠️ <em>You must complete these courses before enrolling in {course_code}.</em>"
        return response
    else:
        return f"Sorry, I couldn't find prerequisite information for {course_code}. Please check the course code."

def format_academic_calendar():
    """Format academic calendar - only shows 2026 events."""
    response = f"<h2 style='color:{HEADER_TEXT};'> Academic Calendar 2026</h2>"

    for category, events in DATA["ACADEMIC_CALENDAR"].items():
        # Filter events for 2026 only
        events_2026 = []
        for event in events:
            try:
                event_date = datetime.strptime(event['date'], '%Y-%m-%d')
                if event_date.year == 2026:
                    events_2026.append(event)
            except:
                continue  # Skip invalid dates
        
        # Skip category if no 2026 events
        if not events_2026:
            continue
        
        response += f"<h3 style='color:{TEXT_COLOR};'>{category.replace('_',' ').title()}</h3>"

        response += f"""
        <table style="width:100%; border-collapse:collapse; background:{ROW_BG_1}; color:{TEXT_COLOR};">
        <thead>
            <tr style="background:{HEADER_BG}; color:{HEADER_TEXT};">
                <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Event</th>
                <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Date</th>
                <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Notes</th>
            </tr>
        </thead><tbody>
        """

        for i, event in enumerate(events_2026):
            bg = ROW_BG_1 if i % 2 == 0 else ROW_BG_2
            response += f"""
            <tr style="background:{bg};">
                <td style="border:1px solid {BORDER_COLOR}; padding:10px;"><b>{event['name']}</b></td>
                <td style="border:1px solid {BORDER_COLOR}; padding:10px;">{event['date']}</td>
                <td style="border:1px solid {BORDER_COLOR}; padding:10px; color:{SUBTEXT_COLOR};"><em>{event.get('notes','')}</em></td>
            </tr>
            """

        response += "</tbody></table><br>"

    return response

def search_calendar_by_keyword(keyword):
    """Search academic calendar by keyword - only 2026 events."""
    keyword_lower = keyword.lower()
    results = []
    
    for category, events in DATA["ACADEMIC_CALENDAR"].items():
        for event in events:
            # Check if event is in 2026
            try:
                event_date = datetime.strptime(event['date'], '%Y-%m-%d')
                if event_date.year != 2026:
                    continue  # Skip non-2026 events
            except:
                continue  # Skip events with invalid dates
            
            # Check if keyword matches
            if (keyword_lower in event['name'].lower() or 
                (event.get('notes') and keyword_lower in event['notes'].lower())):
                results.append({
                    'category': category,
                    'event': event,
                    'date_obj': event_date
                })
    
    if not results:
        return f"No events found matching '{keyword}' in the 2026 academic calendar."
    
    response = f"<strong>Events matching '{keyword}' (2026):</strong><br><br>"
    
    for result in results:
        event = result['event']
        formatted_date = result['date_obj'].strftime('%B %d, %Y')
        
        response += f"• <strong>{event['name']}</strong><br>"
        response += f"  📅 {formatted_date}<br>"
        if 'notes' in event and event['notes']:
            response += f"  ℹ️ {event['notes']}<br>"
        response += "<br>"
    
    return response

# -------------------
# Formatting Functions
# -------------------

def format_courses(semester, show_faculty=True):
    courses = DATA["COURSES"].get(semester, [])
    if not courses:
        return None

    response = f"<strong style='color:{HEADER_TEXT};'>Semester {semester} Courses</strong><br><br>"

    response += f"""
    <table style="width:100%; border-collapse:collapse; background:{ROW_BG_1}; color:{TEXT_COLOR};">
    <thead>
        <tr style="background:{HEADER_BG}; color:{HEADER_TEXT};">
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Code</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Course Name</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px; text-align:center;">Credits</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px; text-align:center;">Theory</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px; text-align:center;">Lab</th>
    """

    if show_faculty:
        response += f"<th style='border:1px solid {BORDER_COLOR}; padding:12px;'>Instructor</th>"

    response += "</tr></thead><tbody>"

    total_credits = 0
    for i, course in enumerate(courses):
        bg = ROW_BG_1 if i % 2 == 0 else ROW_BG_2
        faculty = DATA["COURSE_TO_FACULTY"].get(course['code'], "TBA")

        response += f"""
        <tr style="background:{bg};">
            <td style="border:1px solid {BORDER_COLOR}; padding:10px; color:{HEADER_TEXT};"><b>{course['code']}</b></td>
            <td style="border:1px solid {BORDER_COLOR}; padding:10px;">{course['name']}</td>
            <td style="border:1px solid {BORDER_COLOR}; padding:10px; text-align:center;">{course['credits']}</td>
            <td style="border:1px solid {BORDER_COLOR}; padding:10px; text-align:center;">{course['theory_hours']}</td>
            <td style="border:1px solid {BORDER_COLOR}; padding:10px; text-align:center;">{course['lab_hours']}</td>
        """

        if show_faculty:
            response += f"<td style='border:1px solid {BORDER_COLOR}; padding:10px; color:{SUBTEXT_COLOR};'>{faculty}</td>"

        response += "</tr>"
        total_credits += course['credits']

    response += f"""
    </tbody></table>
    <strong style="color:{HEADER_TEXT};">📚 Total Credits: {total_credits}</strong>
    """

    return response


def format_single_event(event):
    """Format a single event nicely."""
    try:
        event_date = datetime.strptime(event['date'], '%Y-%m-%d')
        formatted_date = event_date.strftime('%B %d, %Y')
    except:
        formatted_date = event['date']
    response = f"<strong>{event['name']}</strong><br><br>"
    response += f"📝 {event['description']}<br>"
    response += f"📅 {formatted_date}<br>"
    response += f"🕐 {event['time']}<br>"
    return response

def format_events():
    """Format all events nicely."""
    response = "<strong>Upcoming University Events:</strong><br><br>"
    for event in DATA["EVENTS"]:
        try:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            formatted_date = event_date.strftime('%B %d, %Y')
        except:
            formatted_date = event['date']
        response += f"• <strong>{event['name']}</strong><br>"
        response += f"  📝 {event['description']}<br>"
        response += f"  📅 {formatted_date} | {event['time']}<br><br>"
    return response

def format_faculty(faculty_name=None):
    response = f"<h3 style='color:{HEADER_TEXT};'>👨‍🏫 Faculty Members </h3>"

    response += f"""
    <table style="width:100%; border-collapse:collapse; background:{ROW_BG_1}; color:{TEXT_COLOR};">
    <thead>
        <tr style="background:{HEADER_BG}; color:{HEADER_TEXT};">
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Name</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Designation</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Email</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Courses Teaching</th>
        </tr>
    </thead><tbody>
    """

    faculty_items = DATA["FACULTY"].items()

    # FILTER IF SPECIFIC FACULTY REQUESTED
    if faculty_name and faculty_name in DATA["FACULTY"]:
        faculty_items = [(faculty_name, DATA["FACULTY"][faculty_name])]

    for i, (key, faculty) in enumerate(faculty_items):
        bg = ROW_BG_1 if i % 2 == 0 else ROW_BG_2
        
        # Get courses taught by this faculty
        courses_taught = faculty.get('courses', [])
        courses_list = ", ".join(courses_taught) if courses_taught else "N/A"
        
        response += f"""
        <tr style="background:{bg};">
            <td style="border:1px solid {BORDER_COLOR}; padding:10px; color:{HEADER_TEXT};">
                <b>{faculty['name']}</b>
            </td>
            <td style="border:1px solid {BORDER_COLOR}; padding:10px;">
                {faculty['designation']}
            </td>
            <td style="border:1px solid {BORDER_COLOR}; padding:10px; color:{SUBTEXT_COLOR};">
                {faculty['email']}
            </td>
            <td style="border:1px solid {BORDER_COLOR}; padding:10px; color:{TEXT_COLOR};">
                {courses_list}
            </td>
        </tr>
        """

    response += "</tbody></table>"
    return response

def get_semester_faculty(semester):
    """Get all faculty teaching in a specific semester in dark-theme tabular form."""
    courses = DATA["COURSES"].get(semester, [])
    if not courses:
        return None

    semester_faculty = set()
    faculty_courses = {}

    # Collect faculty teaching in this semester
    for course in courses:
        faculty_name = DATA["COURSE_TO_FACULTY"].get(course['code'])
        if faculty_name:
            semester_faculty.add(faculty_name)
            faculty_courses.setdefault(faculty_name, []).append({
                'code': course['code'],
                'name': course['name'],
                'schedule': course.get('schedule', 'TBA')
            })

    if not semester_faculty:
        return None

    response = f"""
    <h3 style="color:{HEADER_TEXT}; margin-bottom:10px;">
        👨‍🏫 Faculty Teaching in Semester {semester}
    </h3>
    """

    response += f"""
    <table style="width:100%; border-collapse:collapse;
    background:{ROW_BG_1}; color:{TEXT_COLOR};">
    <thead>
        <tr style="background:{HEADER_BG}; color:{HEADER_TEXT};">
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Faculty</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Designation</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Email</th>
            <th style="border:1px solid {BORDER_COLOR}; padding:12px;">Courses Teaching</th>
        </tr>
    </thead>
    <tbody>
    """

    for i, faculty_name in enumerate(sorted(semester_faculty)):
        faculty_key = extract_faculty_name(faculty_name)
        if faculty_key and faculty_key in DATA["FACULTY"]:
            faculty = DATA["FACULTY"][faculty_key]
            bg = ROW_BG_1 if i % 2 == 0 else ROW_BG_2

            # Courses list
            courses_list = f"<ul style='margin:0; padding-left:18px; color:{TEXT_COLOR};'>"
            for course_info in faculty_courses.get(faculty_name, []):
                courses_list += f"""
                <li style="margin-bottom:6px;">
                    <strong style="color:{HEADER_TEXT};">{course_info['code']}</strong>
                    – {course_info['name']}<br>
                    <small style="color:{SUBTEXT_COLOR};">
                        📅 {course_info['schedule']}
                    </small>
                </li>
                """
            courses_list += "</ul>"

            response += f"""
            <tr style="background:{bg};">
                <td style="border:1px solid {BORDER_COLOR}; padding:10px; color:{HEADER_TEXT};">
                    <strong>{faculty['name']}</strong>
                </td>
                <td style="border:1px solid {BORDER_COLOR}; padding:10px;">
                    {faculty['designation']}
                </td>
                <td style="border:1px solid {BORDER_COLOR}; padding:10px; color:{SUBTEXT_COLOR};">
                    {faculty['email']}
                </td>
                <td style="border:1px solid {BORDER_COLOR}; padding:10px;">
                    {courses_list}
                </td>
            </tr>
            """

    response += "</tbody></table>"
    return response

def format_gpa_info():
    """Format GPA calculation info."""
    response = "🎓 <strong>GPA Calculator Guide:</strong><br><br>"
    response += "<strong>Grading System:</strong><br>" + DATA["FAQ"]["grading"] + "<br><br>"
    response += "<strong>Grade Points:</strong><br>"
    response += "• A = 4.0<br>• B = 3.0<br>• C = 2.0<br>• D = 1.0<br>• F = 0.0<br><br>"
    response += "<strong>Formula:</strong><br>"
    response += "GPA = (Sum of Grade Points × Credits) / Total Credits<br><br>"
    response += "<em>Example:</em> A=4 in 3-credit, B=3 in 4-credit → GPA = ((4*3)+(3*4))/7 = 3.43"
    return response



def check_faq(user_input):
    """Check if input matches FAQ."""
    user_lower = user_input.lower()
    for keyword, response in DATA["FAQ"].items():
        if keyword in user_lower:
            return response
    faq_variations = {
        "timing": "campus timings", "time": "campus timings", "hours": "campus timings",
        "book": "library", "grade": "grading", "gpa system": "grading",
        "marks": "grading", "holiday": "holidays", "vacation": "holidays",
        "break": "holidays", "admission": "admission", "entry": "admission",
        "requirement": "admission", "intern": "internships", "placement": "internships"
    }
    for variation, faq_key in faq_variations.items():
        if variation in user_lower:
            return DATA["FAQ"].get(faq_key)
    return None

def generate_greeting():
    return "Welcome to University Chatbot👋"


def generate_goodbye():
    goodbyes = [
        "Goodbye! Have a great day! 👋",
        "See you later! Feel free to come back anytime.",
        "Bye! Good luck with your studies!",
        "Take care! Let me know if you need help again."
    ]
    return random.choice(goodbyes)

# -------------------
# Load Data
# -------------------
def load_data():
    """Loads real university data for the chatbot."""
    courses_raw = [
        ("CSC101","Introduction to Computing",2,1,3,1),
        ("CSC102","Programming Fundamentals",3,1,4,1),
        ("ASC116","Applied Physics",3,0,3,1),
        ("HSC121","Communication Skills",3,0,3,1),
        ("HSC102","Islamic Studies / Ethics",2,0,2,1),
        ("CSC103","Object Oriented Programming",3,1,4,2),
        ("CSC108","Discrete Structures",3,0,3,2),
        ("CSC111","Digital Logic Design",3,1,4,2),
        ("ASC111","Calculus & Analytical Geometry",3,0,3,2),
        ("HSC111","English Composition & Comprehension",3,0,3,2),
        ("HSC105","Pakistan Studies",2,0,2,2),
        ("CSC201","Data Structures & Algorithms",3,1,4,3),
        ("CSC202","Computer Organization & Assembly Language",3,1,4,3),
        ("ASC112","Linear Algebra",3,0,3,3),
        ("HSC211","Technical & Business Writing",3,0,3,3),
        ("CSE101","Software Engineering Principles",3,0,3,3),
        ("CSC203","Operating Systems",3,1,4,4),
        ("CSC204","Database Systems",3,1,4,4),
        ("CSC206","Computer Architecture",3,0,3,4),
        ("CIC201","Artificial Intelligence",3,0,3,4),
        ("ASC202","Multivariate Calculus",3,0,3,4),
        ("CNS301","Computer Networks",3,1,4,5),
        ("CSC205","Theory of Automata",3,0,3,5),
        ("ASC201","Probability & Statistics",3,0,3,5),
        ("CSC304","Advanced Database Management Systems",2,1,3,5),
        ("MSC203","Principles of Management",3,0,3,5),
        ("HSC110","Civics and Community Engagement",2,0,2,5),
        ("CSC301","Design & Analysis of Algorithms",3,0,3,6),
        ("CSC302","Parallel & Distributed Computing",3,0,3,6),
        ("CNS302","Information Security",3,0,3,6),
        ("CSE204","Human Computer Interaction",3,0,3,6),
        ("DEE101","Domain Elective – I",2,1,3,6),
        ("DEE102","Domain Elective – II",2,1,3,6),
        ("CSC303","Compiler Construction",3,0,3,7),
        ("MSC301","Technopreneurship",3,0,3,7),
        ("DEE103","Domain Elective – III",2,1,3,7),
        ("DEE104","Domain Elective – IV",2,1,3,7),
        ("ESE101","Elective Supporting – I",3,0,3,7),
        ("CSC496","Capstone Project – I",0,3,3,8),
        ("HSC311","Computing Professional Practices",3,0,3,8),
        ("DEE105","Domain Elective – V",3,0,3,8),
        ("DEE106","Domain Elective – VI",3,0,3,8),
        ("DEE107","Domain Elective – VII",3,0,3,8),
        ("CSC497","Capstone Project – II",0,3,3,8)
    ]
    
    COURSES = {}
    for code, name, theory, lab, credits, sem in courses_raw:
        sem_str = str(sem)
        if sem_str not in COURSES:
            COURSES[sem_str] = []
        COURSES[sem_str].append({
            "code": code,
            "name": name,
            "theory_hours": theory,
            "lab_hours": lab,
            "credits": credits
        })
    
    # NEW: Course Prerequisites
    PREREQUISITES = {
        # Semester 1 (No prerequisites)
        "CSC101": [],
        "CSC102": [],
        "ASC116": [],
        "HSC121": [],
        "HSC102": [],
        
        # Semester 2
        "CSC103": ["CSC102"],
        "CSC108": [],
        "CSC111": ["CSC101"],
        "ASC111": [],
        "HSC111": ["HSC121"],
        "HSC105": [],
        
        # Semester 3
        "CSC201": ["CSC103", "CSC108"],
        "CSC202": ["CSC111"],
        "ASC112": ["ASC111"],
        "HSC211": ["HSC111"],
        "CSE101": ["CSC103"],
        
        # Semester 4
        "CSC203": ["CSC201"],
        "CSC204": ["CSC201"],
        "CSC206": ["CSC202"],
        "CIC201": ["CSC201", "ASC112"],
        "ASC202": ["ASC111"],
        
        # Semester 5
        "CNS301": ["CSC203"],
        "CSC205": ["CSC108"],
        "ASC201": ["ASC111"],
        "CSC304": ["CSC204"],
        "MSC203": [],
        "HSC110": [],
        
        # Semester 6
        "CSC301": ["CSC201", "CSC205"],
        "CSC302": ["CSC203"],
        "CNS302": ["CNS301"],
        "CSE204": ["CSE101"],
        "DEE101": [],
        "DEE102": [],
        
        # Semester 7
        "CSC303": ["CSC301"],
        "MSC301": ["MSC203"],
        "DEE103": [],
        "DEE104": [],
        "ESE101": [],
        
        # Semester 8
        "CSC496": [],
        "HSC311": [],
        "DEE105": [],
        "DEE106": [],
        "DEE107": [],
        "CSC497": ["CSC496"]
    }
    
    # NEW: Academic Calendar
    ACADEMIC_CALENDAR = {
        "SPRING_2026": [
            {"name": "Spring Semester Registration Opens", "date": "2026-01-05", "notes": "Online registration portal opens"},
            {"name": "Spring Semester Begins", "date": "2026-01-15", "notes": "First day of classes"},
            {"name": "Add/Drop Deadline", "date": "2026-01-25", "notes": "Last day to add or drop courses"},
            {"name": "Midterm Exams Week", "date": "2026-03-15", "notes": "Midterm examinations"},
            {"name": "Spring Break", "date": "2026-03-22", "notes": "One week break"},
            {"name": "Final Exams Begin", "date": "2026-05-10", "notes": "Final examination period"},
            {"name": "Spring Semester Ends", "date": "2026-05-20", "notes": "Last day of semester"}
        ],
        "FALL_2026": [
            {"name": "Fall Semester Registration Opens", "date": "2026-07-01", "notes": "Online registration portal opens"},
            {"name": "Fall Semester Begins", "date": "2026-08-15", "notes": "First day of classes"},
            {"name": "Add/Drop Deadline", "date": "2026-08-25", "notes": "Last day to add or drop courses"},
            {"name": "Midterm Exams Week", "date": "2026-10-15", "notes": "Midterm examinations"},
            {"name": "Final Exams Begin", "date": "2026-12-10", "notes": "Final examination period"},
            {"name": "Fall Semester Ends", "date": "2026-12-20", "notes": "Last day of semester"},
            {"name": "Winter Break Begins", "date": "2026-12-21", "notes": "Holiday break starts"}
        ],
        "HOLIDAYS": [
            {"name": "Kashmir Day", "date": "2026-02-05", "notes": "Public holiday"},
            {"name": "Pakistan Day", "date": "2026-03-23", "notes": "Public holiday"},
            {"name": "Eid-ul-Fitr", "date": "2026-04-20", "notes": "Approximate date (subject to moon sighting)"},
            {"name": "Labour Day", "date": "2026-05-01", "notes": "Public holiday"},
            {"name": "Eid-ul-Adha", "date": "2026-06-27", "notes": "Approximate date (subject to moon sighting)"},
            {"name": "Independence Day", "date": "2026-08-14", "notes": "Public holiday"},
            {"name": "Iqbal Day", "date": "2026-11-09", "notes": "Public holiday"},
            {"name": "Quaid-e-Azam's Birthday", "date": "2026-12-25", "notes": "Public holiday"}
        ],
        "IMPORTANT_DEADLINES": [
            {"name": "Scholarship Applications Open", "date": "2026-01-10", "notes": "Submit before deadline"},
            {"name": "Internship Registration Deadline", "date": "2026-04-30", "notes": "For summer internships"},
            {"name": "Transcript Request Deadline", "date": "2026-05-15", "notes": "For graduating students"},
            {"name": "Fee Payment Deadline - Spring", "date": "2026-01-20", "notes": "Avoid late fee penalty"},
            {"name": "Fee Payment Deadline - Fall", "date": "2026-08-20", "notes": "Avoid late fee penalty"}
        ]
    }
    
    faculty_raw = [
        ("Sir Jawad Ahmad", "Assistant Professor", "Computer Science", "jawad@uni.edu", ["CSC101", "CSC102"]),
        ("Miss Hafsa Nadeem", "Associate Professor", "Computer Science", "hafsa@uni.edu", ["CSC103", "CSC108"]),
        ("Mr Hamza Ehtisham", "Lecturer", "Computer Science", "hamza@uni.edu", ["CSC111", "ASC116"]),
        ("Dr Ayesha Khan", "Assistant Professor", "Computer Science", "ayesha@uni.edu", ["CSC201", "CSC202"]),
        ("Mr Ali Raza", "Lecturer", "Computer Science", "ali@uni.edu", ["ASC111", "ASC112"]),
        ("Dr Sana Iqbal", "Associate Professor", "Computer Science", "sana@uni.edu", ["CSC203", "CSC204"]),
        ("Ms Maria Shah", "Lecturer", "Computer Science", "maria@uni.edu", ["HSC121", "HSC111"]),
        ("Dr Bilal Tariq", "Assistant Professor", "Computer Science", "bilal@uni.edu", ["CSC206", "CIC201"]),
        ("Mr Usman Farooq", "Lecturer", "Computer Science", "usman@uni.edu", ["HSC211", "HSC311"]),
        ("Dr Samina Javed", "Assistant Professor", "Computer Science", "samina@uni.edu", ["CSE101", "CSE204"]),
        ("Dr Omar Khalid", "Associate Professor", "Computer Science", "omar@uni.edu", ["CNS301", "CNS302"]),
        ("Ms Hina Malik", "Lecturer", "Computer Science", "hina@uni.edu", ["CSC205", "CSC301"]),
        ("Dr Ahmed Farooq", "Assistant Professor", "Computer Science", "ahmed@uni.edu", ["CSC302", "CSC303"]),
        ("Ms Sana Shah", "Lecturer", "Computer Science", "sana.shah@uni.edu", ["ASC201", "ASC202"]),
        ("Mr Kamran Ali", "Assistant Professor", "Computer Science", "kamran@uni.edu", ["CSC304", "MSC203"]),
        ("Dr Fariha Iqbal", "Associate Professor", "Computer Science", "fariha@uni.edu", ["DEE101", "DEE102"]),
        ("Ms Rabia Khan", "Lecturer", "Computer Science", "rabia@uni.edu", ["DEE103", "DEE104"]),
        ("Dr Waseem Tariq", "Assistant Professor", "Computer Science", "waseem@uni.edu", ["MSC301", "ESE101"]),
        ("Mr Saad Malik", "Lecturer", "Computer Science", "saad@uni.edu", ["CSC496", "CSC497"]),
        ("Dr Zainab Ahmed", "Assistant Professor", "Computer Science", "zainab@uni.edu", ["DEE105", "DEE106"]),
        ("Ms Iqra Shah", "Lecturer", "Computer Science", "iqra@uni.edu", ["DEE107", "HSC110"]),
    ]
    
    FACULTY = {}
    COURSE_TO_FACULTY = {}
    FACULTY_TO_COURSES = {}
    
    for name, designation, dept, email, courses in faculty_raw:
        key = name.lower().replace("sir ", "").replace("miss ", "").replace("mr ", "").replace("ms ", "").replace("dr ", "")
        FACULTY[key] = {
            "name": name,
            "designation": designation,
            "dept": dept,
            "email": email,
            "courses": courses
        }
        
        # Build course to faculty mapping
        for course_code in courses:
            if course_code not in COURSE_TO_FACULTY:
                COURSE_TO_FACULTY[course_code] = name
        
        # Build faculty to courses mapping
        FACULTY_TO_COURSES[name] = courses
    
    EVENTS = [
        {"id": 1, "name": "Tech Fest", "description": "Technology exhibition", "date": "2026-03-05", "time": "10:00 AM"},
        {"id": 2, "name": "Workshop on AI", "description": "Hands-on AI workshop", "date": "2026-03-10", "time": "02:00 PM"},
        {"id": 3, "name": "Midterm Exams", "description": "Midterm exams start", "date": "2026-03-15", "time": "09:00 AM"},
        {"id": 4, "name": "Student Week", "description": "Cultural and sports", "date": "2026-03-20", "time": "All Day"},
        {"id": 5, "name": "Guest Lecture: Cybersecurity", "description": "Industry expert session", "date": "2026-03-25", "time": "11:00 AM"}
    ]
    
    FAQ_RESPONSES = {
        "campus timings": "Campus timings: 8:00 AM – 5:00 PM, Monday to Friday.",
        "library": "Library timings: 9:00 AM – 6:00 PM, Monday to Saturday.",
        "grading": "Grading System: A (Excellent), B (Good), C (Average), D (Pass), F (Fail).",
        "holidays": "University holidays include public holidays and semester breaks.",
        "admission": "Admission Requirements: HSC-II ≥50%, Entry Test ≥50% or USAT ≥50%",
        "internships": "Internship mandatory after 4th semester. Minimum 8 weeks."
    }
    
    return {
        "COURSES": COURSES,
        "EVENTS": EVENTS,
        "FACULTY": FACULTY,
        "FAQ": FAQ_RESPONSES,
        "COURSE_TO_FACULTY": COURSE_TO_FACULTY,
        "FACULTY_TO_COURSES": FACULTY_TO_COURSES,
        "PREREQUISITES": PREREQUISITES,
        "ACADEMIC_CALENDAR": ACADEMIC_CALENDAR
    }

DATA = load_data()

# -------------------
# Flask Routes
# -------------------
@app.route("/")
def home():
    session.clear()
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "Please enter a message."}), 400

    # Check if user is saying goodbye FIRST
    user_lower = user_input.lower()
    goodbye_keywords = ['bye', 'goodbye', 'see you', 'exit', 'quit', 'later']
    if any(keyword in user_lower for keyword in goodbye_keywords):
        reply = generate_goodbye()
        session.clear()
        return jsonify({"reply": reply})

    fsm = get_fsm_from_session()
    pda = get_pda_from_session()

    # ---------------------------
    # USER IDENTIFICATION FLOW
    # ---------------------------
    if 'user_name' not in session:
        if 'awaiting_name' not in session:
            session['awaiting_name'] = True
            pda.push("ASK_NAME")
            save_fsm_to_session(fsm)
            save_pda_to_session(pda)
            return jsonify({"reply": f"{generate_greeting()}<br><br>What is your name?"})
        else:
            session['user_name'] = user_input.strip()
            session.pop('awaiting_name', None)
            session['awaiting_dept'] = True
            pda.pop()
            pda.push("ASK_DEPT")
            save_fsm_to_session(fsm)
            save_pda_to_session(pda)
            return jsonify({
                "reply": f"Nice to meet you, {session['user_name']}! Which department are you in?"
            })

    elif 'user_dept' not in session:
        if 'awaiting_dept' not in session:
            session['awaiting_dept'] = True
            pda.push("ASK_DEPT")
            save_fsm_to_session(fsm)
            save_pda_to_session(pda)
            return jsonify({
                "reply": f"{session['user_name']}, which department are you in?"
            })
        else:
            session['user_dept'] = user_input.strip()
            session.pop('awaiting_dept', None)
            pda.pop()
            save_fsm_to_session(fsm)
            save_pda_to_session(pda)
            return jsonify({
                "reply": f"Hey {session['user_name']} from {session['user_dept']}! How can I help you today?"
            })

    # ---------------------------
    # MAIN CHAT LOGIC (FSM + PDA)
    # ---------------------------
    pda.add_history(user_input, getattr(fsm, 'state', 'GENERAL_QUERY'))
    context = pda.top()

    # FSM transition
    state = fsm.transition(user_input)

    # Track FSM history
    fsm_history = session.get('fsm_history', ['START'])
    fsm_history.append(state)
    if len(fsm_history) > 10:
        fsm_history.pop(0)
    session['fsm_history'] = fsm_history

    reply = "I'm here to help! Ask me about courses, faculty, events, or more."

    try:
        if context and context not in ['ASK_NAME', 'ASK_DEPT']:

            if context == 'NEED_SEMESTER_NUMBER':
                semester = extract_semester_number(user_input)
                if semester and semester in DATA["COURSES"]:
                    reply = format_courses(semester)
                    pda.pop()
                else:
                    reply = "Please enter a valid semester number (1–8)."

            elif context == 'NEED_FACULTY_NAME':
                faculty_key = extract_faculty_name(user_input)
                reply = format_faculty(faculty_key)
                pda.pop()

            elif context == 'NEED_COURSE_CODE':
                course_code = extract_course_code(user_input)
                if course_code:
                    reply = get_course_prerequisites(course_code)
                    pda.pop()
                else:
                    reply = "Please provide a valid course code (e.g., CSC201)."

        else:
            faq_response = check_faq(user_input)
            specific_event_match = extract_event_name(user_input)

            if "prerequisite" in user_lower or "prereq" in user_lower:
                course_code = extract_course_code(user_input)
                if course_code:
                    reply = get_course_prerequisites(course_code)
                else:
                    pda.push('NEED_COURSE_CODE')
                    reply = "Which course do you want prerequisites for?"

            elif "calendar" in user_lower or "schedule" in user_lower:
                reply = format_academic_calendar()

            elif faq_response:
                reply = faq_response

            elif "internship" in user_lower:
                reply = format_internships()

            elif specific_event_match:
                reply = format_single_event(specific_event_match)

            elif state == "COURSE_QUERY":
                pda.push('NEED_SEMESTER_NUMBER')
                reply = "Which semester's courses do you want? (1–8)"

            elif state == "FACULTY_QUERY":
                semester = extract_semester_number(user_input)
                faculty_key = extract_faculty_name(user_input)

                if semester:
                    reply = get_semester_faculty(semester)
                elif faculty_key:
                    reply = format_faculty(faculty_key)
                else:
                    reply = format_faculty()

            elif state == "EVENT_QUERY":
                reply = format_events()

            elif state == "GPA_QUERY":
                reply = format_gpa_info()

    except Exception as e:
        print("Chat route error:", e)
        reply = "Sorry, something went wrong. Please try again."

    # Save states
    save_fsm_to_session(fsm)
    save_pda_to_session(pda)

    return jsonify({"reply": reply})

@app.route("/reset", methods=["POST"])
def reset():
    session.clear()
    return jsonify({"status": "Conversation reset successfully!"})

@app.route("/history", methods=["GET"])
def get_history():
    pda = get_pda_from_session()
    return jsonify({"history": pda.get_history(limit=10)})

@app.route("/get_pda_state", methods=["GET"])
def get_pda_state():
    pda = get_pda_from_session()
    fsm = get_fsm_from_session()

    previous_stack = session.get('previous_pda_stack', []).copy()
    current_stack = pda.stack.copy()
    operation = None

    if len(current_stack) > len(previous_stack):
        pushed_item = current_stack[-1] if current_stack else None
        if pushed_item:
            operation = {'type': 'push', 'text': f'PUSH: {pushed_item}'}
    elif len(current_stack) < len(previous_stack):
        popped_item = None
        for i in range(len(previous_stack)-1, -1, -1):
            if i >= len(current_stack) or previous_stack[i] != current_stack[i]:
                popped_item = previous_stack[i]
                break
        if popped_item:
            operation = {'type': 'pop', 'text': f'POP: {popped_item}'}

    session['previous_pda_stack'] = current_stack.copy()
    return jsonify({
        "stack": current_stack,
        "current_state": fsm.state,
        "operation": operation,
        "history": pda.get_history(limit=5)
    })

@app.route("/get_fsm_history", methods=["GET"])
def get_fsm_history():
    fsm_history = session.get('fsm_history', ['START'])
    return jsonify({
        "history": fsm_history,
        "current_state": session.get('fsm_state', 'START')
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)