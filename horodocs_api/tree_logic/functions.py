import binascii
import glob
import hashlib
import os
import uuid
import urllib
import pyqrcode
import ntplib
import pytz
from requests.exceptions import ConnectTimeout, ConnectionError, ReadTimeout
from retry import retry
from datetime import datetime
from .IDQ_quantis import get_true_random
from exceptions import warn_admin
from gettext import gettext as _
import gettext

from settings import (
    TMP_URL,
    WEB_URL,
    BUF_SIZE,
    TMP_URL_QRCODE,
    ACTUAL_VERSION,
    WARN_ADMIN,
)


def create_salt_and_quittance(time):
    """
    Return a random generated salt and a quittance depending on time.

    The quittance is calculated from the sha 256 of the date in parameter. Then we take only the first 128 bits
    Quittance example : 71-7AAA3-2296E5-ECD5E8-D7905D-E7

    Salt example : cf82e2987e6a1eea

    :param: time: Actual date
    :type time: str
    :return: salt, quittance
    :rtype: str, str

    """
    size = 16
    hashed_quitt_id = hash_sha256(time)
    try:
        sel = get_true_random(size, "x", 3)
    except (ConnectTimeout, ConnectionError, ReadTimeout) as e:  # backup
        if WARN_ADMIN:
            warn_admin(e)
        sel = binascii.b2a_hex(os.urandom(size)).decode("utf-8")
    hashed_quitt_id = list(hashed_quitt_id)
    (
        hashed_quitt_id[2],
        hashed_quitt_id[8],
        hashed_quitt_id[15],
        hashed_quitt_id[22],
        hashed_quitt_id[29],
    ) = ("-", "-", "-", "-", "-")
    hashed_quitt_id = hashed_quitt_id[:32]
    hashed_quitt_id = "".join(hashed_quitt_id).upper()
    quittance = hashed_quitt_id
    return sel, quittance


def xor_string(s1, s2):
    """
    Operate a xor between two strings.

    :param s1: First string
    :type s1: str
    :param s2: Second string
    :type s2: str
    :return: XOR generated
    :rtype: str
    """
    print(s1, s2)
    s_xor = [chr(ord(a) ^ ord(b)) for a, b in zip(s1, s2)]
    print("".join(s_xor))
    return "".join(s_xor)


def bytes_xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def hash_sha256(val):
    """
    Return the SHA256 value of the val parameter

    :param val: Value to hash.
    :type val: str
    :return: The SHA256 of val.
    :rtype: str

    """
    return hashlib.sha256(val.encode()).hexdigest()


def hash_file(file):
    """
    Return the SHA256 value of the file in parameter.

    :param file: Path to the file
    :type file: str
    :return: The SHA256 of file.
    :rtype: str

    """
    sha256 = hashlib.sha256()
    with open(file, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def get_hg_hd(data):
    """Separate a string in half and returns each half

    :param data: String to break in half
    :type data: str
    :return: Left part, Right part
    :rtype: str, str
    """
    return data[: len(data) // 2], data[len(data) // 2 :]


def create_qr(md5, sha256, salt, timing, anterior_branches, posterior_branches):
    """
    Create a qr code based on the parameters.

    Use the constants :

    :ref:`TMP_URL <constants>`, :ref:`WEB_URL <constants>`

    :param md5: MD5 value of the submitted file.
    :type md5: str
    :param sha256: SHA256 value of the submitted file.
    :type sha256: str
    :param salt: Salt.
    :type salt: str
    :param timing: Date of the file submission.
    :type timing: str
    :param anterior_branches: List of the green leaves in the Merkle Based Tree.
    :type anterior_branches: List[str]
    :param posterior_branches: List of the orange leaves in the Merkle Based Tree.
    :type posterior_branches: List[str]
    :return: (the qrcode, the qrcode filepath).
    :rtype: (QRCode, str)

    """
    random_name = str(uuid.uuid4()).replace("-", "")
    filename = f"{TMP_URL_QRCODE}qrcode{random_name}.png"
    args = {
        "salt": salt,
        "md5": md5,
        "sha256": sha256,
        "date": timing,
        "anterior_branches": anterior_branches,
        "posterior_branches": posterior_branches,
        "version": ACTUAL_VERSION,
    }
    qrcode_url_redirect = f"{WEB_URL}verification?{str(urllib.parse.urlencode(args))}"

    qrcode = pyqrcode.create(qrcode_url_redirect)
    qrcode.png(f"{filename}", 3)

    return (qrcode, filename)


def find_next_power_of_2(n):
    """
    Function used to find the next power of 2 of the parameter n by putting all used bits to 1.

    Example for 18 (10010) :

        10010 -> 11111

        When we have 11111 we add 1 :

        11111 + 1 -> 100000 -> 32.

    :param n: Value
    :type n: int
    :return: The next power of 2.
    :rtype: int
    """
    # On enlève 1 au cas où le nombre est déjà une puissance de 2. Par exemple, si on a 16, on ne veut pas retourner 32 mais 16.
    n = n - 1

    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    n |= n >> 32

    return n + 1


def is_power_of_2(n):
    """
    Check if n is a power of 2

    :param n: Value
    :type n: int
    :return: True or False.
    :rtype: bool
    """
    return (n & (n - 1) == 0) and n != 0


def delete_tmp_files():
    """
    Delete all tmp files in the folder.
    Use the constants :
        :ref:`TMP_URL <constants>`
    """
    files = glob.glob(f"{TMP_URL_QRCODE}/*")
    # print(os.getcwd())
    for f in files:
        os.remove(f)


def calc_tree_root(leaves, file_value, tree_position, language):
    """
    Calculate the root of the merkle based tree from the file and leaves and make a small explanation of how it's done

    :param leaves: All leaves related to the file (orange and green). Needs to be sorted before this function.
    :type leaves: List[str]
    :param file_value: A SHA256 hash of all file values
    :type file_value: str
    :param tree_position: Position of the file in the merkle based tree.
    :type tree_position: int
    :return: root of the merkle based tree, text describing the process
    :rtype: str, str
    """
    lang = gettext.translation("tree", localedir="locales", languages=[language])
    lang.install()
    _ = lang.gettext
    text_recap_calc_root = ""
    if len(leaves) > 0:
        first_leaf = leaves[0]
        if first_leaf[1] < tree_position:
            tree_root = hash_sha256(first_leaf[2] + file_value)
            text_recap_calc_root += _("Racine de l'arbre = SHA256({} + {})").format(
                first_leaf[2], str(file_value)
            )
            text_recap_calc_root += _("Résultat : {}\n").format(tree_root)
        elif first_leaf[1] > tree_position:
            tree_root = hash_sha256(file_value + first_leaf[2])
            text_recap_calc_root += _("Racine de l'arbre = SHA256({} + {})\n").format(
                str(file_value), first_leaf[2]
            )
            text_recap_calc_root += _("Résultat : {}\n").format(tree_root)
        tree_position = tree_position // 2
        for leaf in leaves:
            if leaf[0] == 0:
                continue
            if leaf[1] < tree_position:
                old_tree_root = tree_root
                tree_root = hash_sha256(leaf[2] + tree_root)
                text_recap_calc_root += _(
                    "Racine de l'arbre = SHA256({} + {})\n"
                ).format(leaf[2], str(old_tree_root))
                text_recap_calc_root += _("Résultat : {}\n").format(tree_root)
            elif leaf[1] > tree_position:
                old_tree_root = tree_root
                tree_root = hash_sha256(tree_root + leaf[2])
                text_recap_calc_root += _(
                    "Racine de l'arbre = SHA256({} + {})\n"
                ).format(str(old_tree_root), leaf[2])
                text_recap_calc_root += _("Résultat : {}\n").format(tree_root)
            tree_position = tree_position // 2
    else:
        tree_root = str(file_value)
        text_recap_calc_root += _("Une seule valeur dans l'arbre.\n")
        text_recap_calc_root += _("Racine de l'arbre = {}\n").format(tree_root)
    return tree_root, text_recap_calc_root


def reformate_date(date):
    """
    Reformate the date from the format YYYY-MM-DDHHMMSS(Zz) to be more human eye-readable.

    Example :

        2022-07-06090800(CEST+0200) becomes 2022-07-06 09:08:00 (CEST+0200)

    :param date: Date to reformat
    :type n: str
    :return: Reformatted date
    :rtype: str
    """
    tmp_date = date.split("-")
    tmp = tmp_date[2].split("(")
    tmp_date2 = tmp[0]
    n = 2
    tmp_date2 = [tmp_date2[i : i + n] for i in range(0, len(tmp_date2), n)]
    return f'{tmp_date[0]}-{tmp_date[1]}-{tmp_date2[0]} {tmp_date2[1]}:{tmp_date2[2]}:{tmp_date2[3]} ({tmp[1].replace("U", " : U")}'


@retry()
def get_now_time():
    """Get actual time from ntp server.

    Use a retry wrapper to make sure that the ntp server responds to us. It can very rarely not.

    :return: Actual time
    :rtype: datetime
    :return: timezone of the time
    :rtype: str
    """
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request("pool.ntp.org")
    ts = datetime.fromtimestamp(response.tx_time)
    tz = pytz.timezone("Europe/Zurich").localize(datetime.now()).strftime("%z")
    formatted_tz = f"Europe/Zurich : UTC{tz}"
    return ts, formatted_tz
