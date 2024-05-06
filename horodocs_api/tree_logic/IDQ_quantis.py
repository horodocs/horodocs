import requests
from dotenv import load_dotenv
import os


def get_true_random(nb_bytes, mode="b", timeout=1):
    """
    Return a photon based random number of bytes
    
    :param: nb_bytes: Number of bytes wanted
    :type time: int
    :param: mode: x for hex and b for base 64
    :type mode: str
    :param: timeout: Seconds before a timeout is observed
    :type timeout: int
    :return: A true random number if possible
    :rtype: str
    :raises ValueError: if the number of bytes is invalid or if the mode is not x or b
    :raises requests.ConnectionError: if the connection has an issue
    """
    dotenv_path = ".env" 
    load_dotenv(dotenv_path)
    server_url = os.environ.get("QUANTUM_GEN_URL")

    if type(nb_bytes) != int or nb_bytes < 1 or nb_bytes > 128:
        raise ValueError("le nombre de byte doit être un entier entre 1 et 128")

    if mode not in ["x", "b"]:
        raise ValueError("le mode doit valoir 'x' pour de l'hexa ou 'b' pour du base64")

    r = requests.get(f'{server_url}/{mode}/{nb_bytes}', timeout=timeout)
    if(r.status_code != 200):
        raise requests.ConnectionError
    return r.text

if __name__ == '__main__':

    nb_bytes = 32
    mode = 'b'

    rand = get_true_random(24, "x")
    print(len(rand))