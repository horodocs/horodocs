from locust import HttpUser, task, between


class User(HttpUser):
    wait_time = between(1, 3)
    headers = {"x-api-key": "r4zqlxBz-UYgj-ymjM-76hN-hQlAsjXe"}


    @task(4)
    def verify_quittance(self):
        params = {'salt': ['d504b0a25582c13f3c72e4ee6ba76ec2'], 
            'md5': ['4390911c086a6fa71b5d93d86abf9991'],
            'sha256': ['fb33aee41af2ffc2d628f1cec0e3e69adee525629c79239897d2e4dedf067548'],
            'date': ['2023-02-28090210(Europe/ZurichUTC+0100)'], 
            'anterior_branches': ["[(0, 18, '4ed61043c0cbb90b2b887371172dec01d46737e39f3b9f2f0b51242633112a90'), (1, 8, '9508a601b483c10a07bbb20e8846b12eb6d203784cd97ef91a2222cd1fcf80e6'), (4, 0, '0aea04b02d87c1a52695e57d47cf83b627ae6e6811a594a3b4e5d0542ffc7c0b')]"], 
            'posterior_branches': ["[(2, 5, 'e675752fa474250d3f42506e3b3d3f4844c5ae28fe9e75838d08c6fecb036e3d'), (3, 3, 'dd7b6e5ebbfd761a21df1e045cbf18b6a16a5f3eeb0fc50be74e3ddbab7096d6')]"], 
            'version': ['1']
        }
        self.client.get(f"verify_receipt/", name="/verify_receipt",params=params, headers=self.headers)

    @task(2)
    def add_leaf(self):
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
        self.client.post(f"add_leaf_tree/", name="/add_leaf_tree",json=params, headers=self.headers)