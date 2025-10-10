import threading
from datetime import datetime
from django.contrib.auth import get_user_model
from django.conf import settings
from core.utils import send_html_email
from django.utils.crypto import get_random_string 
import secrets

def generate_password():
    return get_user_model().objects.make_random_password()


def generate_student_id():
    # Generate a username based on first and last name and registration date
    registered_year = datetime.now().strftime("%Y")
    students_count = get_user_model().objects.filter(is_student=True).count()
    return f"{settings.STUDENT_ID_PREFIX}-{registered_year}-{students_count}"


def generate_lecturer_id():
    # Generate a username based on first and last name and registration date
    registered_year = datetime.now().strftime("%Y")
    lecturers_count = get_user_model().objects.filter(is_lecturer=True).count()
    return f"{settings.LECTURER_ID_PREFIX}-{registered_year}-{lecturers_count}"


def generate_student_credentials():
    return generate_student_id(), generate_password()


def generate_lecturer_credentials():
    return generate_lecturer_id(), generate_password()


class EmailThread(threading.Thread):
    def __init__(self, subject, recipient_list, template_name, context):
        self.subject = subject
        self.recipient_list = recipient_list
        self.template_name = template_name
        self.context = context
        threading.Thread.__init__(self)

    def run(self):
        send_html_email(
            subject=self.subject,
            recipient_list=self.recipient_list,
            template=self.template_name,
            context=self.context,
        )


def send_new_account_email(user, password):
    # Generate activation key and deactivate user
    user.activation_key = secrets.token_urlsafe(32)
    user.is_active = False
    user.save()

    # Choose template based on user type
    if user.is_student:
        template_name = "accounts/email/new_student_account_confirmation.html"
    else:
        template_name = "accounts/email/new_lecturer_account_confirmation.html"

    # Build full confirmation link
    activation_link = f"http://127.0.0.1:8000/en/accounts/confirm-email/{user.activation_key}/"

    # Prepare email
    email = {
        "subject": "Your Placid Academy account confirmation and credentials",
        "recipient_list": [user.email],
        "template_name": template_name,
        "context": {
            "user": user,
            "password": password,
            "activation_link": activation_link,
        },
    }
    # Send it asynchronously
    EmailThread(**email).start()
