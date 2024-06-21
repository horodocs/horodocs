from threading import Lock, Thread
from time import sleep
from smart_contract.eth_interface import Eth
from settings import TRANSACTION_VERIFIER_TIMING, EMAIL_ADMIN
from .mail_sender import EmailMessage
from gettext import gettext as _
import gettext
import logging

class TransactionVerifier(Thread):
    """Transaction Verifier allows to verify transactions in memory. Tells if those transactions are valid or not depending on the number of block confirmations."""

    #: Mutex to make sure that we don't have concurrencies issues.
    mutex = Lock()

    #: List of transactions needed to be verified
    __transactions_to_verify = []

    #: Dictionnary using transactions as key and the value are a list of emails.
    __transactions_mail_link = {}

    #: Dictionnary linking files to mails/transactions. __mails_filenames[(mail, transaction)] = List[filenames]
    __mails_filenames = {}

    def add_transaction(self, transaction_id, mails_filenames):
        """Add a transaction to verify

        :param transaction_id: ID (hash) of the transaction
        :type transaction_id: str
        :param mails_filenames: List of mails and filenames (as a tuple)
        :type mails_filenames: List[str,str,str,str,str] - see want_ancrage_information in tree.py
        """
        self.__transactions_to_verify.append(transaction_id)
        mails = []
        for mf in mails_filenames:
            mails.append((mf[0], mf[4]))
            if not ((mf[0], transaction_id) in self.__mails_filenames):
                self.__mails_filenames[(mf[0], transaction_id)] = [
                    (mf[1], mf[2], mf[3])
                ]
            else:
                self.__mails_filenames[(mf[0], transaction_id)].append(
                    (mf[1], mf[2], mf[3])
                )
        self.__transactions_mail_link[transaction_id] = list(set(mails))

    def verify_transactions(self):
        """Verify transactions on the blockchain ethereum. If transaction is valid, send an email to users and remove the transaction from memory."""
        eth = Eth()
        for t in self.__transactions_to_verify:
            valid = eth.check_transaction_validation(t)
            if valid == 1 or valid == 0:
                # print(f'Transaction validated, sending mails to {self.__transactions_mail_link}')
                self.__send_mail(
                    t, valid == 0
                )  # if valid == 0, the transaction is not valid
                self.__transactions_to_verify.remove(t)
                self.__transactions_mail_link.pop(t)
                keys = self.__mails_filenames.keys()
                key_to_delete = None
                for k in keys:
                    if k[1] == t:
                        key_to_delete = k
                        break
                if key_to_delete != None:
                    self.__mails_filenames.pop(key_to_delete)

    def __send_mail(self, transaction, error=False):
        """Send mails to the users linked to the parameter transaction

        :param transaction: Transaction ID (hash)
        :type transaction: str
        :param error: If an error occured during the validation
        :type error: boolean
        """

        for mail, language in self.__transactions_mail_link[transaction]:
            lang = gettext.translation(
                "tree", localedir="locales", languages=[language]
            )
            lang.install()
            _ = lang.gettext
            subject = _("Informations sur l'ancrage de l'arbre dans la blockchain")
            if not error:
                message = _(
                    "Bonjour,\n\nLa transaction liée aux numéros de quittance ci-dessous a été ancrée avec succès dans la blockchain :\n"
                )
            else:
                message = _(
                    "Bonjour,\n\nLa transaction liée aux numéros de quittance ci-dessous a eu un problème lors de l'ancrage dans la blockchain :\n"
                )
            for filename, case_number, file_id in self.__mails_filenames[
                (mail, transaction)
            ]:
                message += _(
                    "- Numéro de cas : {}, Identifiant du fichier : {} ({})\n"
                ).format(case_number, file_id, filename)

            if error:
                message += _("Merci de bien vouloir recommencer le processus.\n")
            message += _(
                "\nNous vous remercions de votre confiance.\n\nL'équipe Horodatage ESC.\nCet email est envoyé automatiquement, merci de ne pas y répondre."
            )
            recipient = mail
            email_message = EmailMessage(subject, message, EMAIL_ADMIN, recipient)
            try:
                email_message.send()
            except Exception as e:
                logging.error(e)

    def run(self) -> None:
        """Thread's logic. Verify the transactions every :ref:`TRANSACTION_VERIFIER_TIMING <constants>`"""
        while True:
            sleep(TRANSACTION_VERIFIER_TIMING)
            self.mutex.acquire()
            try:
                self.verify_transactions()
            finally:
                self.mutex.release()
