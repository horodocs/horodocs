import ast
import json
import random
import string
from logging.config import dictConfig

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security, status
from sqlalchemy.orm import Session

from api_security import get_admin_api_key, get_api_key, CheckWebsiteHealth
from smart_contract.eth_interface import (
    Eth,
    GetAllContractTransactions,
    deactivate_horodating,
)
from sql_db import db_utils, models, schemas
from sql_db.database import engine, get_db
from tree_logic.functions import *
from tree_logic.tree import LeafInfos, SendTree, TreeBuilder, tree_mutex

from cachetools import TTLCache
from settings import LOG_CONFIG

dictConfig(LOG_CONFIG)

API_KEY_LENGTH = 32

#: Cache for the requests so we don't need to calculate every request if we already have done it.
cache = TTLCache(maxsize=100, ttl=60)

# Load the database
models.Base.metadata.create_all(bind=engine)

# Load FastAPI
app = FastAPI(debug=True)

# Start the SendTree daemon
t = SendTree()
t.daemon = True
t.start()

# Start the ContractTransaction Getter daemon
c = GetAllContractTransactions()
c.daemon = True
c.start()

# Init the smart contract logic to communicate with
bc = Eth()

# Start the website Health check daemon
health_thread = CheckWebsiteHealth("https://horodocs.unil.ch/ht/")
health_thread.daemon = True
health_thread.start()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/ht")
async def get_health():
    """Route to check if the API is running

    :return: Success message
    :rtype: Dict[str,str]
    """
    return {"message": "Success"}


@app.get("/ht_horo")
async def get_horo_health():
    """Get the horodating functionnality health.

    :raises HTTPException: if it is not activated.
    :return: Success message
    :rtype: Dict[str,str]
    """
    if deactivate_horodating.is_set():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Horodating not available for the moment.",
        )
    else:
        return {"message": "Success"}


@app.get("/get_transactions/{timestamp}")
async def get_transactions(timestamp: int, api_key: str = Security(get_api_key)):
    """Get the transactions made with the smart contract at timestamp +- 1hour

    :param timestamp: Timestamp
    :type timestamp: int
    :return: the list of transactions
    :rtype: List[Transaction]
    """
    t1 = timestamp - 3600
    t2 = timestamp + 3600

    with open("contract_transactions.json", "r") as openfile:
        txs = json.load(openfile)
    txs = list(
        filter(
            lambda x: int(x["timeStamp"]) > t1 and int(x["timeStamp"]) < t2,
            txs["result"],
        )
    )
    return txs


@app.get("/check_transaction/{transaction_hash}")
async def get_transactions(transaction_hash: str, api_key: str = Security(get_api_key)):
    """Check if the transaction transaction_hash is finalized.

    :param transaction_hash: Hash of the transaction to check
    :type transaction_hash: str
    :param api_key: APIKey, defaults to Security(get_api_key)
    :type api_key: str, optional
    :return: State of the transaction
    :rtype: int
    """
    return bc.check_transaction_validation(transaction_hash)


@app.put("/update_config/")
async def update_config(
    config: schemas.ConfigItem,
    db: Session = Depends(get_db),
    api_key: str = Security(get_admin_api_key),
):
    """Update the config with config in the database db. Needs admin privileges.

    :param config: Config containing the config name and the config value
    :type config: schemas.ConfigItem
    :param db: database, defaults to Depends(get_db)
    :type db: Session, optional
    :param api_key: API Key, defaults to Security(get_admin_api_key)
    :type api_key: str, optional
    :raises HTTPException: if the config does not exist
    :return: Success message
    :rtype: Dict[str,str]
    """
    conf = db_utils.update_config(
        db=db, config_name=config.name, new_value=config.value
    )
    if conf:
        return {"message": "Success"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid config parameter"
        )


@app.put("/reactivate_horodating/")
async def reactivate_horodating(api_key: str = Security(get_admin_api_key)):
    """Reactivate the horodating functionality. Needs admin privileges.

    :param api_key: APIKey, defaults to Security(get_admin_api_key)
    :type api_key: str, optional
    :return: Success message
    :rtype: Dict[str,str]
    """
    deactivate_horodating.clear()
    return {"message": "Success"}


@app.post("/create_api_key/")
async def create_api_key(
    db: Session = Depends(get_db), api_key: str = Security(get_admin_api_key)
):
    """Create a new random api key. Needs admin privileges.

    :param db: Database, defaults to Depends(get_db)
    :type db: Session, optional
    :param api_key: API Key, defaults to Security(get_admin_api_key)
    :type api_key: str, optional
    :return: Newly created APIKey
    :rtype: models.APIKeys
    """
    generated_key = random.choices(
        string.ascii_letters + string.digits, k=API_KEY_LENGTH
    )
    generated_key[8], generated_key[13], generated_key[18], generated_key[23] = (
        "-",
        "-",
        "-",
        "-",
    )
    key = schemas.APIKeysItem(
        value="".join(generated_key), is_active=True, is_admin=False
    )
    return db_utils.create_api_key_db(db=db, api_key=key)


@app.post("/add_leaf_tree/")
async def add_leaf_tree(leaf_infos: LeafInfos, api_key: str = Security(get_api_key)):
    """Adds a new leaf in the current tree. If the tree is locked, adds the leaf in the waiting list.

    :param leaf_infos: Informations of the new leaf to add
    :type leaf_infos: LeafInfos
    :param api_key: API Key, defaults to Security(get_api_key)
    :type api_key: str, optional
    :raises HTTPException: if horodating is not activated. Meaning this functionality is deactivated
    :return: Success message
    :rtype: Dict[str,str]
    """
    if not deactivate_horodating.is_set():
        ts, tz = get_now_time()
        now_date_readable = f'{ts.strftime("%Y-%m-%d %H:%M:%S")} ({tz})'
        now_date_filename = now_date_readable.replace(" ", "").replace(":", "")

        salt, quittance = create_salt_and_quittance(now_date_filename)

        hash_signature = hash_sha256(
            salt + now_date_filename + leaf_infos.md5_value + leaf_infos.sha256_value
        )
        file_data = (
            salt,
            now_date_filename,
            leaf_infos.md5_value,
            leaf_infos.sha256_value,
            now_date_readable,
        )
        tree = TreeBuilder()
        if (
            tree_mutex.locked()
        ):  # if the tree is finalizing we put the new leaf in the waiting list.
            tree.add_waiting_elem(
                hash_signature, leaf_infos.email_user, leaf_infos, quittance, file_data
            )
        else:
            tree_mutex.acquire()
            try:
                tree.add_elem(
                    hash_signature,
                    leaf_infos.email_user,
                    leaf_infos,
                    quittance,
                    file_data,
                )
                if leaf_infos.want_ancrage_informations:
                    tree.add_mail_ancrage(
                        leaf_infos.email_user,
                        quittance,
                        leaf_infos.case_number,
                        leaf_infos.file_id,
                        leaf_infos.language,
                    )
            finally:
                tree_mutex.release()
        return {"message": "Success"}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Horodating not available for the moment.",
        )


@app.get("/verify_receipt/")
async def verify_receipt(
    salt: str,
    date: str,
    md5: str,
    sha256: str,
    anterior_branches: str,
    posterior_branches: str,
    version: int,
    language: str,
    api_key: str = Security(get_api_key),
):
    """Verify if the receipt is correct.

    :param salt: Salt in the receipt
    :type salt: str
    :param date: Date in the receipt
    :type date: str
    :param md5: MD5 in the receipt
    :type md5: str
    :param sha256: SHA256 in the receipt
    :type sha256: str
    :param anterior_branches: the anterior branches
    :type anterior_branches: str
    :param posterior_branches: the posterior branches
    :type posterior_branches: str
    :param version: Version to work with
    :type version: int
    :param api_key: APIKey, defaults to Security(get_api_key)
    :type api_key: str, optional
    :raises HTTPException: if we don't find the transaction with the smart contract (does not means that the adding didn't work, it can be because the list of transactions is not yet updated)
    :return: Values as a dict for the website to display
    :rtype: dict[str]
    """

    # check if we already treated this receipt in the last minute
    result = cache.get(salt)
    if result is not None:
        # if yes we directly return it
        return result
    file_value = hash_sha256(salt + date + md5 + sha256)

    # we tell FastAPI that the branches are str but they are formatted as a list so we can literal_eval them.
    anterior_branches = ast.literal_eval(anterior_branches)
    posterior_branches = ast.literal_eval(posterior_branches)

    # combining both branches into one
    leaves = [*anterior_branches, *posterior_branches]
    # we sort them so we have for example : (1,0), (2,1), etc...
    leaves_sorted = sorted(leaves, key=lambda tup: tup[0])

    # we need to determine the receipt position in the tree
    if len(leaves_sorted) > 0:
        n = leaves_sorted[0][1] % 2
        if n == 0:
            tree_position = leaves_sorted[0][1] + 1
        else:
            tree_position = leaves_sorted[0][1] - 1
    else:
        tree_position = 0

    # now we can calculate the root of the tree
    tree_root, explanation_text = calc_tree_root(
        leaves_sorted, file_value, tree_position, language
    )
    hg, hd = get_hg_hd(tree_root)

    date = reformate_date(date)

    found_tx = None
    date_transaction = None

    # we check all the transactions in a 2 hour interval so we don't need to check all of them (it's faster).
    dt = date.split(" (")
    dtimezone = dt[1].split(" : ")[1][:-1]
    timestamp = datetime.timestamp(
        datetime.strptime(dt[0] + dtimezone, "%Y-%m-%d %H:%M:%S%Z%z")
    )

    t1 = timestamp - 3600
    t2 = timestamp + 3600

    with open("contract_transactions.json", "r") as openfile:
        txs = json.load(openfile)
    txs = list(
        filter(
            lambda x: int(x["timeStamp"]) > t1 and int(x["timeStamp"]) < t2,
            txs["result"],
        )
    )

    # for each transaction we check if the value corresponds to the receipt (calculated) values
    for tx in txs:
        decoded_value = bc.decode_input_tx(tx["input"])[1]["newTxtid"].split(",")
        if len(decoded_value) > 2:
            cipher = decoded_value[0]
            hd_blockchain = decoded_value[1]
            if hd == hd_blockchain:
                date_validation_arbre = decoded_value[2]
                lid_decrypted = "{:016x}".format(int(cipher, 16) ^ int(hg, 16))
                lid_decrypted = "-".join(
                    lid_decrypted[i : i + 4] for i in range(0, len(lid_decrypted), 4)
                )
                # lid_decrypted = xor_string(cipher, hg)
                found_tx = tx
                validation = bc.check_transaction_validation(tx["hash"])
                date_transaction = datetime.fromtimestamp(
                    int(tx["timeStamp"])
                ).strftime("%Y-%m-%d %H:%M:%S")
                break
            else:
                hd_blockchain = None
    if not found_tx:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction not found."
        )
    dotenv_path = ".env"
    load_dotenv(dotenv_path)
    documentation_address = os.environ.get("HORODOCS_URL_DOCS")

    context = {
        "date": date,
        "md5": md5,
        "sha256": sha256,
        "file_value": file_value,
        "tree_root": tree_root,
        "tree_date": date_validation_arbre,
        "found_tx": found_tx,
        "validation": validation,
        "transaction_date": date_transaction,
        "decrypted_lid": lid_decrypted,
        "hd_blockchain": hd_blockchain,
        "version": version,
        "url_doc": documentation_address,
        "explanation_text": explanation_text,
    }

    # we cache the context to return it faster if the same request comes again.
    if validation == 1:
        cache[salt] = context
    return context
