import binascii
import datetime
import os
import queue
from threading import Lock, Thread
from time import sleep
from typing import Optional

from pydantic import BaseModel
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

from settings import ACTUAL_VERSION, EMAIL_ADMIN, START_WORKING_DAY, END_WORKING_DAY
from smart_contract.eth_interface import Eth
from sql_db.database import engine
from sqlalchemy.orm import sessionmaker

from sql_db.db_utils import get_config

from .functions import (
    bytes_xor,
    create_qr,
    delete_tmp_files,
    find_next_power_of_2,
    get_hg_hd,
    get_now_time,
    hash_sha256,
    is_power_of_2,
    xor_string,
    convert_hexstring_to_binary,
)
from .IDQ_quantis import get_true_random
from .mail_sender import EmailMessage
from .PdfCreator import PdfCreator
from .singleton import Singleton
from .TransactionVerifier import TransactionVerifier
from exceptions import ContractCommunicationException
from smart_contract.eth_interface import deactivate_horodating
from gettext import gettext as _
import gettext
from pathlib import Path

#: Mutex used to remove concurrencies issues.
tree_mutex = Lock()
# waiting_list_mutex = Lock()


class LeafInfos(BaseModel):
    md5_value: str
    sha256_value: str
    case_number: str
    file_id: str
    investigator: str
    email_user: str
    comments: str
    want_ancrage_informations: bool
    language: str
    password: Optional[str]


class TreeBuilder(metaclass=Singleton):
    """Class containing all the logic behind the Merkle Based Tree. This class must be a Singleton to work correctly."""

    #: Number of elements in the current tree
    __nb_elements = 0

    #: Differents parts of the tree
    __parts = {}

    #: Associate a leaf to an email and other user infos. email_leaf_association[leaf] = (email, leaf_infos, file_infos, quittance)
    __email_leaf_association = {}

    #: List containing emails, filename, case_number and file_id of people wanting update of the verification and validation of the transaction.
    want_ancrage_infos = []

    waiting_list = queue.Queue()

    locale_dir = Path("locales")
    gettext.bindtextdomain("horodocs_api", locale_dir)
    gettext.textdomain("horodocs_api")

    def __init__(self) -> None:
        """
        Class initialisation. Will start another thread for the Transaction Verifier.
        """
        self.transaction_verifier = TransactionVerifier()
        self.transaction_verifier.daemon = True
        self.transaction_verifier.start()

    def clear_tree(self):
        """Clear the current tree"""
        self.__nb_elements = 0
        self.__parts = {}
        self.want_ancrage_infos = []

    def add_waiting_elem(
        self, element, email, leaf_infos: LeafInfos, quittance, file_infos
    ):
        self.waiting_list.put((element, email, leaf_infos, quittance, file_infos))

    def transfer_waiting_elem_to_tree(self):
        # print(f"Transfering {self.waiting_list.qsize()} elements to tree...")
        while not self.waiting_list.empty():
            wl = self.waiting_list.get()
            hash_signature = wl[0]
            leaf_infos = wl[2]
            quittance = wl[3]
            file_data = wl[4]
            self.add_elem(
                hash_signature, leaf_infos.email_user, leaf_infos, quittance, file_data
            )
            if leaf_infos.want_ancrage_informations:
                self.add_mail_ancrage(
                    leaf_infos.email_user,
                    quittance,
                    leaf_infos.case_number,
                    leaf_infos.file_id,
                    leaf_infos.language,
                )

    def add_elem(self, element, email, leaf_infos: LeafInfos, quittance, file_infos):
        """Add a new element to the current tree

        :param element: Hash to add the tree
        :type element: str
        :param email: Email of the user linked to the tree
        :type email: str
        :param file_data: All the data contained in the form submitted by the user
        :type file_data: LeafInfos
        :param quittance: Quittance ramdomly generated
        :type quittance: str
        :param file_infos: Different file information, those are the values used to calculate the hash of the added data
        :type file_infos: tuple(str,str,str,str,str)
        :return: Index of the newly added value in the tree
        :rtype: int
        """
        n = self.__nb_elements
        self.__parts[(0, n)] = element
        self.__email_leaf_association[element] = (
            email,
            leaf_infos,
            file_infos,
            quittance,
        )
        self.__calc_tree()
        self.__nb_elements += 1
        return n

    def add_mail_ancrage(self, mail, id_file, case_number, file_id, language):
        """Add the mail-filename association to the list of people wanting update

        :param mail: Mail of the user.
        :type mail: str
        :param filename: Name of the file uploaded by the user
        :type filename: str
        :param case_number: Case number linked to the quittance
        :type case_number: str
        :param file_id: File id linked to the quittance
        :type file_id: str
        :param language: Language wanted by the user
        :type language: str
        """
        self.want_ancrage_infos.append((mail, id_file, case_number, file_id, language))

    def get_anterior_branches(self, n):
        """Get the anterior branches associated to the n leaf

        :param n: Indice of the leaf
        :type n: int
        :return: All the associated anterior branches
        :rtype: List[str]
        """
        vals = []
        i = 0
        j = n
        while j > 0:
            if j % 2 == 1:
                j = j - 1
                vals.append((i, j, self.__parts[(i, j)]))
            j = j // 2
            i = i + 1
        return vals

    def get_posterior_branches(self, n):
        """Get the posterior branches associated to the n leaf

        :param n: Indice of the leaf
        :type n: int
        :return: All the associated posterior branches
        :rtype: List[str]
        :raises ValueError: If the tree has not 2^n number of elements
        """
        if is_power_of_2(self.__nb_elements):
            vals = []
            j = n
            for i in range(self.__get_tree_depth()):
                if j % 2 == 0:
                    j = j + 1
                    vals.append((i, j, self.__parts[(i, j)]))
                j = (j - 1) // 2

            return vals
        else:
            raise ValueError(
                "The tree has not 2^n number of elements, complete the tree before using this function."
            )

    def get_nb_elems(self):
        """Get the number of elements in the current tree.

        :return: Number of elements in the tree
        :rtype: int
        """
        return self.__nb_elements

    def __calc_tree(self):
        """Update the tree with the new calculated leaves and subleaves."""
        i = 0
        j = self.__nb_elements

        while (j % 2) == 1:
            self.__parts[(i + 1, (j - 1) // 2)] = hash_sha256(
                self.__parts[(i, j - 1)] + self.__parts[(i, j)]
            )
            j = (j - 1) // 2
            i = i + 1

    def __get_tree_depth(self):
        """Get the depth of the tree

        :return: Depth of the tree
        :rtype: int
        """
        depth = 0
        j = self.__nb_elements
        # on compte le nombre de décalage de bits pour obtenir la profondeur.
        while j > 1:
            depth += 1
            j = j >> 1  # on decale tous les bits de j vers la droite (ex: 1000 -> 0100)
        return depth

    def finalize_tree(self):
        """Finalize the tree. Make sure that the tree has 2^n number of elements by completing the missing leaves with random values."""
        tree_final_size = find_next_power_of_2(self.__nb_elements)
        for _ in range(self.__nb_elements, tree_final_size):
            self.add_elem(str(binascii.b2a_hex(os.urandom(32))), None, None, None, None)

    def get_root(self):
        """Get the root of the current merkle based tree.

        :raises ValueError: If the tree has not 2^n number of elements
        :return: Value of the root
        :rtype: str
        """
        if is_power_of_2(self.__nb_elements):
            return self.__parts[(self.__get_tree_depth(), 0)]
        else:
            raise ValueError(
                "The tree has not 2^n number of elements, complete the tree before using this function."
            )

    def send_pdfs(self, time2, lid):
        """Create and send the pdf quittance to all the users related to the tree.

        Adds the root of the tree to the current logs journal.

        :param time2: Time of closure of the tree
        :type time2: str
        :param lid: LID generated for all the pdf of this tree
        :type lid: str
        :raises ValueError: If the tree has not 2^n number of elements
        """
        if is_power_of_2(self.__nb_elements):
            for n in range(self.__nb_elements):
                leaf = self.__parts[(0, n)]
                anterior_branches = self.get_anterior_branches(n)
                posterior_branches = self.get_posterior_branches(n)
                infos_tree = self.__email_leaf_association[leaf]
                email = infos_tree[0]
                if email == None:  # if randomly completed, there is no email
                    continue
                file_data = infos_tree[2]
                leaf_infos = infos_tree[1]
                quittance = infos_tree[3]
                lang = gettext.translation(
                    "tree", localedir="locales", languages=[leaf_infos.language]
                )
                lang.install()
                _ = lang.gettext
                pdf_filename = _("Registre_Quittance_{}_{}.pdf").format(
                    file_data[1], quittance
                )
                qr_code, qr_name = create_qr(
                    file_data[2],
                    file_data[3],
                    file_data[0],
                    file_data[1],
                    anterior_branches,
                    posterior_branches,
                )
                pdf_builder = PdfCreator(
                    file_name=quittance,
                    language=leaf_infos.language,
                    password=leaf_infos.password,
                )
                pdf_builder.add_title(_("QUITTANCE DE L'HORODATAGE AVEC CODE QR"))
                pdf_builder.add_qr_code(qr_name, qr_code.data)
                pdf_builder.add_category(_("Informations sur le fichier horodaté :"))
                pdf_builder.add_horodatage_trace(file_data[4])
                pdf_builder.add_empreintes_trace(
                    leaf_infos.md5_value, leaf_infos.sha256_value
                )
                pdf_builder.add_information_rect(
                    _(
                        "Lors d’une vérification, assurez-vous que la date et les empreintes numériques du fichier correspondent à celles qui sont imprimées ci-dessus."
                    )
                )

                pdf_builder.add_category(_("Informations générales :"))
                pdf_builder.add_informations_trace(
                    leaf_infos.case_number,
                    leaf_infos.file_id,
                    leaf_infos.investigator,
                    leaf_infos.comments,
                )

                pdf_builder.add_category(_("Enregistrement dans la blockchain :"))

                pdf_builder.add_blockchain_values(lid, time2, "Sepolia-Ethereum (Test)")
                pdf_builder.add_information_rect(
                    _(
                        "Lors de la vérification, afin de corroborer que l’horodatage a été retrouvé dans la blockchain, une valeur témoin est retournée. Elle doit correspondre à celle imprimée sur la quittance."
                    )
                )

                pdf_builder.add_category(_("Informations techniques :"))
                pdf_builder.add_technical_informations(
                    _(
                        "Les informations techniques suivantes permettent de retrouver cet horodatage dans la blockchain soit manuellement, soit via la programmation d’un autre système de vérification indépendant."
                    ),
                    file_data[0],
                    anterior_branches,
                    posterior_branches,
                    ACTUAL_VERSION,
                )
                pdf_builder.add_information_rect(
                    _(
                        "Clause de non-responsabilité : <br/>Cette quittance a été générée par la version {} du système d’horodatage développé par l’ESC de l'Université de Lausanne.<br/>Ce système est mis à disposition gratuitement en l’état et n’engage la responsabilité ni de l’ESC, ni de l'UNIL, ni de l’équipe de développement. La version actuelle du système utilise une blockchain test gratuite, similaire à Ethereum, mais dont l’intégrité ne peut être garantie."
                    ).format(ACTUAL_VERSION)
                )
                pdf = pdf_builder.build_pdf()

                subject = _("Votre quittance pour le fichier {}").format(
                    leaf_infos.file_id
                )
                message = _(
                    "Bonjour, vous trouverez en pièce-jointe le pdf correspondant à l'horodatage de votre fichier ayant pour identifiant {}, appartenant au cas {} et fait le {}.\n\n Nous vous remercions de votre confiance.\n\n L'équipe Horodatage ESC.\n Cet email est envoyé automatiquement, merci de ne pas y répondre."
                ).format(leaf_infos.file_id, leaf_infos.case_number, file_data[4])

                recipient = email
                email_message = EmailMessage(subject, message, EMAIL_ADMIN, recipient)
                email_message.attach(filename=pdf_filename, content=pdf.read())
                email_message.send()
        else:
            raise ValueError(
                "The tree has not 2^n number of elements, complete the tree before using this function."
            )

    def send_root_to_chain(self, root_value):
        """Send the current tree root to the smartcontract

        :param root_value: root of the tree
        :type root_value: str
        """
        blockchain_publique = Eth()
        self.hash_transaction = blockchain_publique.send_new_value(root_value)
        self.transaction_verifier.mutex.acquire()
        try:
            self.transaction_verifier.add_transaction(
                self.hash_transaction, self.want_ancrage_infos
            )
        finally:
            self.transaction_verifier.mutex.release()

    def __str__(self):
        """Used to print the tree in the console

        :return: Constructed string of the tree
        :rtype: str
        """
        keys = self.__parts.keys()
        build_str = ""
        for k in keys:
            if k[0] == 0:
                build_str += f"{k[1]} = {self.__parts[k]}\n"
            else:
                build_str += f"{k} = {self.__parts[k]}\n"
        return build_str


class SendTree(Thread):
    """Thread class running in background used to close the current tree and create a new one every x minutes depending on the time of day and a database value."""

    def run(self):
        """Run class where the tree is stored. The tree is then finalized and send to the smart contract."""
        tree = TreeBuilder()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        while True:
            today = datetime.datetime.today()
            dayoftheweek = today.weekday()
            if dayoftheweek < 5:  # mon-fri
                if (
                    today.hour < START_WORKING_DAY and today.hour > END_WORKING_DAY
                ):  # at night
                    sleep(int(get_config(SessionLocal(), "night_config").value) * 60)
                else:
                    sleep(int(get_config(SessionLocal(), "day_config").value) * 60)
            else:  # weekend
                sleep(int(get_config(SessionLocal(), "weekend_config").value) * 60)
            if deactivate_horodating.is_set():
                print("can't send tree for now...")
                continue
            tree_mutex.acquire()
            try:
                if tree.get_nb_elems() > 0:
                    print("Finalizing tree...")
                    tree.finalize_tree()
                    root = tree.get_root()

                    ts, tz = get_now_time()
                    t2 = f'{ts.strftime("%Y-%m-%d %H:%M:%S")} ({tz})'
                    hg, hd = get_hg_hd(root)
                    try:
                        lid = get_true_random(8, mode="x")
                    except (ConnectTimeout, ConnectionError, ReadTimeout) as e:
                        lid = binascii.b2a_hex(os.urandom(8)).decode("utf-8")
                    # cipher_text = xor_string(int(hg, 16), lid)
                    hgg, hgd = get_hg_hd(hg)
                    cipher_text = bytes_xor(
                        convert_hexstring_to_binary(hgg),
                        convert_hexstring_to_binary(hgd),
                    )
                    cipher_text = bytes_xor(
                        cipher_text, convert_hexstring_to_binary(lid)
                    ).hex()
                    lid = "-".join(lid[i : i + 4] for i in range(0, len(lid), 4))
                    try:
                        tree.send_root_to_chain(f"{cipher_text},{hd}, {t2}")
                    except ContractCommunicationException:
                        continue
                    tree.send_pdfs(t2, lid)
            finally:
                delete_tmp_files()
                tree.clear_tree()
                tree.transfer_waiting_elem_to_tree()
                tree_mutex.release()


if __name__ == "__main__":
    tree = TreeBuilder()
    tree2 = TreeBuilder()
    leaves_to_test = [0, 3, 9, 14, 27]
    for i in range(32):
        tree.add_elem(f"{i}")
        # if(i in leaves_to_test):
        # print(tree2.get_anterior_branches(i))
    tree.finalize_tree()
    # for i in leaves_to_test:
    #     print(tree.get_posterior_branches(i))
    print(tree2)
