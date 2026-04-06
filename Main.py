#Import statments
import json
import os
import smtplib
from email.mime.text import MIMEText

#Configuration Settings
CANVAS_TOKEN = os.environ.get("CANVAS_TOKEN")
CANVAS_BASE  = "https://ucf.instructure.com"

#Secret Vars
GMAIL_ADDRESS  = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS")
YOUR_VERIZON   = os.environ.get("YOUR_VERIZON")

#Grades Files
GRADES_FILE = "grades.json"

#Coruses that matter
COURSES_TO_TRACK = [
    "Calculus 3",
    "Computer Science 2",
    "Physics 2",
    "Systems Software",
]

#Function to get grades
def get_grades():
    headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}

    #Try-Except to fetch courses
    try:
        #Calling Token
        response = requests.get(
            f"{CANVAS_BASE}/api/v1/courses?enrollment_state=active&per_page=50",
            headers=headers
        )
        response.raise_for_status()
        courses = response.json()
    #Except error
    except Exception as e:
        print(f"Error fetching courses: {e}")
        return {}

    #Initilizing array
    grades = {}
    #For to navigate course
    for course in courses:
        #Skipping over not interested in courses
        if not isinstance(course, dict) or "id" not in course:
            continue

        #Getting course name
        course_name = course.get("name", f"Course {course['id']}")

        #Try-Except tree
        try:
            #Calling token
            enroll_response = requests.get(
                f"{CANVAS_BASE}/api/v1/courses/{course['id']}/enrollments?user_id=self",
                headers=headers
            )
            enroll_response.raise_for_status()
            enrollments = enroll_response.json()
        #Except error when fail to fetch enrollment
        except Exception as e:
            print(f"Error fetching enrollment for {course_name}: {e}")
            continue

        #Getting vars for each course/enrollment
        for enrollment in enrollments:
            if enrollment.get("type") == "StudentEnrollment":
                score = enrollment.get("grades", {}).get("current_score")
                grade = enrollment.get("grades", {}).get("current_grade")
                grades[course_name] = {"score": score, "grade": grade}

    #Returning
    return grades

#Func to send msg
def send_text(message):
    #Try except tree to format msg
    try:
        #Formatting msg with secret vars
        msg = MIMEText(message)
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = YOUR_VERIZON
        msg["Subject"] = ""

        #Logging in to gmail/phone properly to send
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            server.sendmail(GMAIL_ADDRESS, YOUR_VERIZON, msg.as_string())

        #Confirmation of error
        print(f"Text sent: {message}")
    except Exception as e:
        print(f"Error sending text: {e}")

#Func to check grades with prev grades
def check_grades():
    #Checking grades
    print("Checking grades...")

    #Setting up curr grades
    current = get_grades()
    current = {k: v for k, v in current.items() if k in COURSES_TO_TRACK}

    #Error in case no grades present
    if not current:
        print("No grades returned — check your Canvas token.")
        return

    #Else/if grades do exist
    if os.path.exists(GRADES_FILE):
        with open(GRADES_FILE, "r") as f:
            previous = json.load(f)

        #For to set up vars for iterations of grades
        for course, data in current.items():
            prev = previous.get(course, {})
            curr_score = data.get("score")
            prev_score = prev.get("score")

            #Checking to see if equal
            if curr_score != prev_score:
                #Fromat to see if grade posted or changed
                if prev_score is None:
                    msg = f"Grade posted in {course}: {curr_score}%"
                else:
                    msg = f"{course}: {prev_score}% → {curr_score}%"

                #Sending the msg
                send_text(msg)
                
    #Else if error/no grades
    else:
        print("No previous grades file found — saving current grades as baseline.")
        print("You'll get texts next time something changes.")

    #Save current grades for next run
    with open(GRADES_FILE, "w") as f:
        json.dump(current, f, indent=2)

    #Successful print
    print("Done. Current grades:")
    for course, data in current.items():
        print(f"  {course}: {data.get('score')}% ({data.get('grade')})")

#Running program
if __name__ == "__main__":
    check_grades()









