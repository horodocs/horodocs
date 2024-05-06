import email, smtplib, ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from settings import EMAIL_HOST

from dotenv import load_dotenv
import os
from pathlib import Path


class EmailMessage():
    def __init__(self, subject, body, sender, receiver) -> None:
        self.subject = subject
        self.body = body
        self.sender = sender
        self.receiver = receiver

        # Create a multipart message and set headers
        self.message = MIMEMultipart()
        self.message["From"] = self.sender
        self.message["To"] = self.receiver
        self.message["Subject"] = self.subject
        # Add body to email
        self.message.attach(MIMEText(self.body, "plain"))

    def attach(self, filename, content):

        self.part = MIMEBase("application", "octet-stream")
        self.part.set_payload(content)

        # Encode file in ASCII characters to send by email    
        encoders.encode_base64(self.part)

        # Add header as key/value pair to attachment part
        self.part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )
        # Add attachment to message and convert message to string
        self.message.attach(self.part)

    def send(self):
        self.complete_email = self.message.as_string()
        dotenv_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
        load_dotenv(dotenv_path)
        # Log in to server using secure context and send email
        context = ssl.create_default_context()
        server = smtplib.SMTP(EMAIL_HOST, 587)
        server.starttls(context=context)
        server.login(os.environ.get("EMAIL_USER"), os.environ.get("EMAIL_PASSWORD"))
        server.sendmail(self.sender, self.receiver, self.complete_email)
