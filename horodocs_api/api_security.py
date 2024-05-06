import logging
from fastapi import HTTPException, status, Security, Depends
from fastapi.security import APIKeyHeader
from sql_db.database import get_db
from sql_db.db_utils import get_api_key_db
from sqlalchemy.orm import Session
import requests
from threading import Thread
from time import sleep
from exceptions import warn_admin
from settings import WARN_ADMIN, HEALTH_CHECK_TIMING

#: Header for the APIKey is x-api-key
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

logger = logging.getLogger("health_check_logger")

def get_api_key(api_key_header: str = Security(api_key_header), db: Session = Depends(get_db)):
    """Check if the API key passed in x-api-key is in the database db. Parameters should not be used. 

    :raises HTTPException: Error 401 if invalid or missing API key
    :return: API Key in db if it exists
    :rtype: models.APIKeys
    """
    if(api_key_header):
        res = get_api_key_db(db=db, api_key=api_key_header)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")
    
    if(res):
        if api_key_header == res.value and res.is_active:
            return res
    

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")

def get_admin_api_key(api_key_header: str = Depends(get_api_key)):
    """Check if the API key is admin

    :raises HTTPException: Error 401 if key is not admin
    :return: API Key
    :rtype: models.APIKeys
    """
    if(api_key_header.is_admin):
        return api_key_header
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insufficient Privileges")

class CheckWebsiteHealth(Thread):
    """Background class to check if the Website is alive and well running. If WARN_ADMIN is True, warn the administrator in setting of a potential issue if there is one.
    The HealthCheck is every HEALTH_CHECK_TIMING
    """
    def __init__(self, website_address):
        super(CheckWebsiteHealth, self).__init__()
        self.website_address = website_address
    def run(self):       
        headers = {'Accept': 'application/json'}
        while True:
            try:
                r = requests.get(self.website_address, headers=headers, verify=False)
                if(r.ok):
                    content = r.json()
                    keys = content.keys()
                    problems = []
                    for k in keys:
                        if(content[k] != 'working'):
                            problems.append(k)
                            logger.error(f"A website error occured for {k}")
                    if(len(problems) > 0 and WARN_ADMIN):
                        warn_admin(f"An error occured the website healthcheck for the following flags : {problems}")
                else:
                    if(WARN_ADMIN):
                        warn_admin(f"The website health route has responded with an error {r.status_code}")
                    logger.error(f"The website health route has responded with an error {r.status_code}")
            except (requests.ConnectTimeout, requests.ConnectionError, requests.ReadTimeout) as e:
                if(WARN_ADMIN):
                    warn_admin(f"The website appears to have a problem : {e}")
                logger.critical(e)
            sleep(HEALTH_CHECK_TIMING)
