import requests
from threading import Thread
import time
import argparse
from statistics import mean

class StressTest(Thread):
    def __init__(self, id, url, params, headers, n_requests=40, post=False):
        Thread.__init__(self)
        self.id = id
        self.url = url
        self.params = params
        self.headers = headers
        self.n_requests = n_requests
        self.post = post
        self.results = []

    def run(self):
        for i in range(self.n_requests):
            if(self.post):
                params["case_number"] = f"Case {str(i)}"
                params['investigator'] = f"Enqueteur {str(self.id)}"
            t = time.time()
            if(self.post):
                r = requests.post(self.url, json=self.params, headers=self.headers)
            else:
                r = requests.get(self.url, params=self.params, headers=self.headers)
            if(r.status_code == 200):
                self.results.append(time.time() - t)
            else:
                self.results.append(-1)
            time.sleep(0.01)

 
parser = argparse.ArgumentParser(description="API Stress Tester",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-u", "--users", type=int, default=5, help="Number of concurrent users wanted")
parser.add_argument("-n", "--number-requests", type=int, default=10, help="Number of requests per user")
parser.add_argument("-m", "--mode", type=int, default=0, help="What API route will be stressed")
args = parser.parse_args()
config = vars(args)


threads = []
concurent_users = config['users']
n_requests = config['number_requests']
mode = config['mode']
headers = {"x-api-key": "r4zqlxBz-UYgj-ymjM-76hN-hQlAsjXe"}
post = False
if(mode == 0):
    url = "http://127.0.0.1:8001/verify_receipt/"
    params = {'salt': ['d504b0a25582c13f3c72e4ee6ba76ec2'], 
            'md5': ['4390911c086a6fa71b5d93d86abf9991'],
            'sha256': ['fb33aee41af2ffc2d628f1cec0e3e69adee525629c79239897d2e4dedf067548'],
            'date': ['2023-02-28090210(Europe/ZurichUTC+0100)'], 
            'anterior_branches': ["[(0, 18, '4ed61043c0cbb90b2b887371172dec01d46737e39f3b9f2f0b51242633112a90'), (1, 8, '9508a601b483c10a07bbb20e8846b12eb6d203784cd97ef91a2222cd1fcf80e6'), (4, 0, '0aea04b02d87c1a52695e57d47cf83b627ae6e6811a594a3b4e5d0542ffc7c0b')]"], 
            'posterior_branches': ["[(2, 5, 'e675752fa474250d3f42506e3b3d3f4844c5ae28fe9e75838d08c6fecb036e3d'), (3, 3, 'dd7b6e5ebbfd761a21df1e045cbf18b6a16a5f3eeb0fc50be74e3ddbab7096d6')]"], 
            'version': ['1']
    }
elif(mode == 1):
    url = "http://127.0.0.1:8001/add_leaf_tree/"
    params = {
        "md5_value":"md5",
        "sha256_value":"sha256",
        "case_number":"case number",
        "file_id":"id_file",
        "investigator":"enqueteur",
        "email_user":"horodocs.esc@gmail.com",
        "comments":"coucou",
        "want_ancrage_informations":True
    }
    post = True
for i in range(concurent_users):
    # Création d'un objet de la classe RequestThread pour chaque itération
    thread = StressTest(i, url,params, headers, n_requests, post)
    # Ajout de l'objet à la liste
    threads.append(thread)
    # Démarrage du thread
    thread.start()

# Attendre la fin de tous les threads
for thread in threads:
    thread.join()

results = []
for thread in threads:
    results = results + thread.results

errors = results.count(-1)
results = list(filter(lambda x: x > 0, results))
min_time = min(results)
max_time = max(results)
avg_time = mean(results)

print(f"With {concurent_users} concurent users making {n_requests} requests each, the API took {avg_time} seconds on average to respond. The lowest response time was {min_time} and the highest was {max_time}.")
print(f"{errors} requests had a problem and didn't work.")