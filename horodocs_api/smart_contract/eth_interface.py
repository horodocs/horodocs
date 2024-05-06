import sys
from web3 import Web3, exceptions
from dotenv import load_dotenv
import json, os
from pathlib import Path
from web3.middleware import geth_poa_middleware
import requests
from threading import Thread, Event
from time import sleep
import json
from settings import REFRESH_JSON_TRANSACTIONS_TIMING, WARN_ADMIN, MIN_ETHEREUM
from retry import retry
from exceptions import EtherscanAPIException, warn_admin, ContractCommunicationException
import logging

deactivate_horodating = Event()
logger = logging.getLogger("smart-contract-logger")


class Eth:
    """
    Class to interact with the smart contract
    """

    def __init__(self, verifiy_balance=False):
        """Init all the parameters necessary to communicate with the smart contract. Also check the ethereum balance if verifiy_balance is True.

        :param verifiy_balance: If we want to check the balance at init
        :type veifiy_balance: Boolean
        """
        self.dotenv_path = ".env"
        load_dotenv(self.dotenv_path)
        contract_path = Path(os.environ.get("CONTRACT_PATH"))
        self.contract_address = os.environ.get("CONTRACT_ADDRESS")
        self.w3 = Web3(Web3.HTTPProvider(os.environ.get("API_URL")))
        self.abi = self.load_abi(contract_path)

        self.private_key = os.environ.get("PRIVATE_KEY")

        self.public_key = os.environ.get("PUBLIC_KEY")
        self.w3.eth.default_account = self.public_key
        if verifiy_balance:
            balance = self.w3.fromWei(self.w3.eth.getBalance(self.public_key), "ether")
            if balance < MIN_ETHEREUM:
                if WARN_ADMIN:
                    warn_admin(f"Ethereum balance low at {balance} ether")
        # if(os.environ.get("TESTNET")):
        #     self.w3.middleware_onion.inject(geth_poa_middleware, layer=0) # for PoA ethereum goerly testnet
        self.contract = self.w3.eth.contract(
            address=self.contract_address, abi=self.abi
        )

    def get_last_ethereum_block_number(self):
        """Get the last ethereum block number.

        :return: Last ethereum block number
        :rtype: int
        """
        return self.w3.eth.get_block_number()

    def get_last_finalized_block_number(self):
        """Get the last finalized ethereum block number.

        :return: Last finalized ethereum block number
        :rtype: int
        """
        return self.w3.eth.get_block("finalized")["number"]

    def check_transaction_validation(self, transac_id):
        """Check if the block containing the transaction has been validated and if finalized

        :param transac_id: Transaction's hash to check
        :type transac_id: str
        :return: Four value int (0,1,2,-1) representing 4 states (Not valid, valid, validation in progress, error)
        :rtype: int
        """
        last_eth_finalized_block_nb = self.get_last_finalized_block_number()
        try:
            transaction_block_number = self.get_transac_block_number(transac_id)
        except exceptions.TransactionNotFound:
            return 0
        # print(f'Last block {last_eth_block_nb}, Transaction block {transaction_block_number}')
        try:
            if last_eth_finalized_block_nb > transaction_block_number:
                return 1
            else:
                return 2
        except TypeError:
            return -1

    def get_transac_block_number(self, transac_id):
        """Get the block number of a given transaction

        :param transac_id: Transaction identification
        :type transac_id: str
        :return: Number of the block containing the transaction
        :rtype: int
        """
        return self.w3.eth.get_transaction(transaction_hash=transac_id)["blockNumber"]

    def get_actual_value(self):
        """Get the value stocked in the smart contract currently

        :return: Stocked value
        :rtype: str
        """
        txtid = self.contract.functions.getTxtid().call()
        return txtid

    def get_transac_value(self, transac_id):
        """Get the value send to the contract from a given transaction

        :param transac_id: Transaction ID
        :type transac_id: str
        :return: Value contained in the transaction at the time
        :rtype: str
        """
        transac = self.w3.eth.get_transaction(transac_id)
        func_obj, func_params = self.contract.decode_function_input(transac["input"])
        return func_params["newTxtid"]

    def get_transac_timestamp(self, transac_id):
        """Get the timestamp of the transaction's block

        :param transac_id: Transaction ID
        :type transac_id: str
        :return: Timestamp of the block
        :rtype: int
        """

        receipt = self.w3.eth.wait_for_transaction_receipt(transac_id)
        bloc_number = receipt["blockNumber"]
        bloc_timestamp = self.w3.eth.get_block(bloc_number)["timestamp"]
        return bloc_timestamp

    @retry(
        logger=logger, tries=5, delay=3, backoff=3
    )  # 3secs, 9secs, 27secs, 81secs, 243secs
    def send_new_value(self, newValue):
        """Send a new value to update the smart contract

        Uses the retry wrapper to try again 3secs, 9secs, 27secs, 81secs and 243secs later if an exception is raised.
        If the exception is raised, deactivate the horodating system. If after a retry, there is no issue, the horodating is reactivated.

        :param newValue: New value to store in the smart contract
        :type newValue: str
        :return: Transaction ID or -1 if error
        :rtype: str
        :raises ContractCommunicationException: if there is an issue to communicate with the smart contract.
        """
        nonce = self.w3.eth.get_transaction_count(self.public_key)
        tx = self.contract.functions.updateTxtid(newValue).buildTransaction(
            {"nonce": nonce}
        )
        signed_tx = self.w3.eth.account.sign_transaction(
            tx, private_key=self.private_key
        )
        try:
            result = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        except ValueError as v:  # for example : not enough funds
            if WARN_ADMIN:
                warn_admin(v)
            logger.critical(v)
            deactivate_horodating.set()
            raise ContractCommunicationException(
                f"A Problem occured during smart contract communication : {v}"
            )
        deactivate_horodating.clear()
        balance = self.w3.fromWei(self.w3.eth.getBalance(self.public_key), "ether")
        if balance < MIN_ETHEREUM:
            if WARN_ADMIN:
                warn_admin(f"Ethereum balance low at {balance} ether")
        return result.hex()

    def get_verification_url(self, transac_id):
        """Get verification URL of a transaction

        :param transac_id: Transaction ID
        :type transac_id: str
        :return: URL of the transaction
        :rtype: str
        """

        return f"https://sepolia.etherscan.io/tx/{transac_id}"

    @staticmethod
    def load_abi(path_to_contract):
        """Load the smart contract ABI

        :param path_to_contract: Local path to the smart contract JSON
        :type path_to_contract: str
        :return: JSON abi information
        :rtype: str
        """
        with open(path_to_contract) as f:
            info_json = json.load(f)

        return info_json["abi"]

    def get_all_contract_transactions(self):
        """Get all the transactions made to the smart contract

        :return: All transactions
        :rtype: JSON
        """
        params = {
            "module": "account",
            "action": "txlist",
            "address": self.contract_address,
            "sort": "asc",
            "apikey": os.environ.get("ETHERSCAN_API_KEY"),
        }
        # we need to tell the etherscan API that we are a legit user
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        r = requests.get(
            url=os.environ.get("ETHERSCAN_API_URL"),
            params=params,
            headers=headers,
            timeout=10,
        )
        # extracting data in json format
        try:
            data = r.json()
        except requests.exceptions.JSONDecodeError as e:
            logging.debug(r)
            raise e
        if int(data["status"]) == 1:
            return data
        else:
            raise EtherscanAPIException(
                "An error occured when communicating with Etherscan API."
            )

    def decode_input_tx(self, input):
        """Decode the input thanks to the decode function of the smart contract

        :param input: Input to decode
        :type input: str
        :return: Input decoded
        :rtype: str
        """
        decoded_input = self.contract.decode_function_input(input)
        return decoded_input


class GetAllContractTransactions(Thread):
    """Threading class that periodically retrieve all the smart contract transactions."""

    def run(self):
        bc = Eth(verifiy_balance=True)
        error = False
        while True:
            try:
                transactions = bc.get_all_contract_transactions()
            except requests.exceptions.ReadTimeout:
                logging.warning(
                    "The connection to the Etherscan API timed out. Retrying."
                )
                continue
            except (requests.exceptions.JSONDecodeError, EtherscanAPIException) as e:
                logging.error(e)
                if WARN_ADMIN:
                    warn_admin(e)
                error = True
            if not error:
                j = json.dumps(transactions, indent=4)
                with open("contract_transactions.json", "w") as f:
                    f.write(j)
            error = False
            sleep(REFRESH_JSON_TRANSACTIONS_TIMING)
