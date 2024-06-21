from settings import EMAIL_ADMIN, PROJECT_ADMIN
from tree_logic.mail_sender import EmailMessage
import datetime

class EtherscanAPIException(Exception):
    pass

class ContractCommunicationException(Exception):
    pass

def warn_admin(exception):
    """Function to send a report directly to the admin via email.

    :param exception: Problem that has occured during runtime
    :type exception: Exception
    """
    subject = "Problème API Horodocs"
    date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    message = f"Bonjour,\n\nL'erreur suivante est apparue le {date} :\n\n {exception}"
    email_message = EmailMessage(
                    subject,
                    message,
                    EMAIL_ADMIN,
                    PROJECT_ADMIN[1]
                )
    email_message.send()