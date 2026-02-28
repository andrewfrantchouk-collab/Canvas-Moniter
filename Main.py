import requests
import json
import os
import smtplib
from email.mime.text import MIMEText

# ── CONFIG ──────────────────────────────────────────────────────────────────
CANVAS_TOKEN = "1158~4wTUyM62RffEA84e7CQe7M4kf3M7Qt7yA96YNk8tefu9DBCUZPBJnXaWEaHxuhLU"
CANVAS_BASE  = "https://ucf.instructure.com"

GMAIL_ADDRESS  = "andrewfrantchouk@gmail.com"     # The Gmail you'll send FROM
GMAIL_APP_PASS = "wdnq ergu pbrc ammt"      # Gmail App Password (see setup guide)
YOUR_VERIZON   = "19169533234@vtext.com"     # Your 10-digit number + @vtext.com

GRADES_FILE = "grades.json"                 # Stores previous grades locally
# ────────────────────────────────────────────────────────────────────────────

COURSES_TO_TRACK = [
    "Calculus 3",
    "Computer Science 2",
    "COP3402-26Spring 0013",
    "Physics 2",
    "Systems Software",
]

def get_grades():
    """Pull current scores for all active Canvas courses."""
    headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}

    try:
        response = requests.get(
            f"{CANVAS_BASE}/api/v1/courses?enrollment_state=active&per_page=50",
            headers=headers
        )
        response.raise_for_status()
        courses = response.json()
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return {}

    grades = {}
    for course in courses:
        if not isinstance(course, dict) or "id" not in course:
            continue

        course_name = course.get("name", f"Course {course['id']}")

        try:
            enroll_response = requests.get(
                f"{CANVAS_BASE}/api/v1/courses/{course['id']}/enrollments?user_id=self",
                headers=headers
            )
            enroll_response.raise_for_status()
            enrollments = enroll_response.json()
        except Exception as e:
            print(f"Error fetching enrollment for {course_name}: {e}")
            continue

        for enrollment in enrollments:
            if enrollment.get("type") == "StudentEnrollment":
                score = enrollment.get("grades", {}).get("current_score")
                grade = enrollment.get("grades", {}).get("current_grade")
                grades[course_name] = {"score": score, "grade": grade}

    return grades


def send_text(message):
    """Send a text via Verizon email-to-SMS gateway using Gmail."""
    try:
        msg = MIMEText(message)
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = YOUR_VERIZON
        msg["Subject"] = ""  # Keep subject empty so the body shows up cleanly

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            server.sendmail(GMAIL_ADDRESS, YOUR_VERIZON, msg.as_string())

        print(f"Text sent: {message}")
    except Exception as e:
        print(f"Error sending text: {e}")


def check_grades():
    """Compare current grades to saved grades and text on any change."""
    print("Checking grades...")
    current = get_grades()
    current = {k: v for k, v in current.items() if k in COURSES_TO_TRACK}
    
    if not current:
        print("No grades returned — check your Canvas token.")
        return

    if os.path.exists(GRADES_FILE):
        with open(GRADES_FILE, "r") as f:
            previous = json.load(f)

        for course, data in current.items():
            prev = previous.get(course, {})
            curr_score = data.get("score")
            prev_score = prev.get("score")

            if curr_score != prev_score:
                # Format nicely depending on whether scores exist
                if prev_score is None:
                    msg = f"Grade posted in {course}: {curr_score}% ({data.get('grade', 'N/A')})"
                else:
                    direction = "▲" if (curr_score or 0) > (prev_score or 0) else "▼"
                    msg = f"{direction} Grade change in {course}: {prev_score}% → {curr_score}% ({data.get('grade', 'N/A')})"

                send_text(msg)

    else:
        print("No previous grades file found — saving current grades as baseline.")
        print("You'll get texts next time something changes.")

    # Save current grades for next run
    with open(GRADES_FILE, "w") as f:
        json.dump(current, f, indent=2)

    print("Done. Current grades:")
    for course, data in current.items():
        print(f"  {course}: {data.get('score')}% ({data.get('grade')})")


if __name__ == "__main__":

    check_grades()


