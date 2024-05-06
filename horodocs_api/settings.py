import os
from dotenv import load_dotenv
# Build paths inside the project like this: BASE_DIR / 'subdir'.
load_dotenv(".env")

#: Project admin name and email
PROJECT_ADMIN = ("name", "xxx@mail.com")

#: If admin needs to be warned in case of failure
WARN_ADMIN = True

#: After how much seconds the api needs to verify that the website is still working
HEALTH_CHECK_TIMING = 120

#: Admin email used to send mails to users
EMAIL_ADMIN = os.environ.get("EMAIL")

#: Email hostname
EMAIL_HOST = os.environ.get("EMAIL_HOST")

#: Temporary files folder path
TMP_URL = f'{os.getcwd()}/static/tmp/quittances/'

#: Temporary QR codes folder path
TMP_URL_QRCODE = f'{os.getcwd()}/static/tmp/qrcodes/'

#: Web server URL
WEB_URL = "https://horodocs.unil.ch/"


#: Maximal size of the buffer to hash files.
BUF_SIZE = 65536 

#: URL of the header img used in the pdf.
HORODOCS_HEADER_IMG_URL = f"{os.getcwd()}/static/img/Poster-header_2.png"

#: Actual version of the system
ACTUAL_VERSION = 1

#: Contact email for the pdf
CONTACT_EMAIL = "horodatage@unil.ch"

#: Contact name for the pdf
CONTACT_NOM = "NAME"

#: Start work day hour
START_WORKING_DAY = 7

#: End work day hour
END_WORKING_DAY = 18

#: The transaction verifier will verify transactions each TRANSACTION_VERIFIER_TIMING seconds.
TRANSACTION_VERIFIER_TIMING = 30

#: Refresh the transactions linked to the smart contract (in seconds)
REFRESH_JSON_TRANSACTIONS_TIMING = 300

#: Minimum ethereum in the wallet before warning the admin to put more funds in it
MIN_ETHEREUM = 1

#: Logging configuration
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",

        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "horodocs-api-logger": {"handlers": ["default"], "level": "DEBUG"},
        "smart-contract-logger": {"handlers": ["default"], "level": "DEBUG"},
    },
}
