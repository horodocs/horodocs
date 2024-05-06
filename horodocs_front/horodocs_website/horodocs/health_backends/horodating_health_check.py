from health_check.backends import BaseHealthCheckBackend, HealthCheckException
from horodocs_website.settings import API_URL
import requests

class HorodatingHealthCheckBackend(BaseHealthCheckBackend):
    #: The status endpoints will respond with a 200 status code
    #: even if the check errors.
    critical_service = True

    def check_status(self):
        # The test code goes here.
        # You can use `self.add_error` or
        # raise a `HealthCheckException`,
        # similar to Django's form validation.
        full_url = API_URL+"ht_horo"
        try:
            response = requests.get(full_url, verify=False)
            if(not response.ok):
                raise HealthCheckException("Horodating is not available for the moment.")
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
            raise HealthCheckException("API is not working")
        # print(response)
        

    def identifier(self):
        return self.__class__.__name__  # Display name on the endpoint.
