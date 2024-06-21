from sqlalchemy.orm import Session

from . import models, schemas

def get_config(db: Session, config_name: str):
    """Return the value corresponding to config_name in the database

    :param db: Database
    :type db: Session
    :param config_name: Name of the wanted config
    :type config_name: str
    :return: Config value
    :rtype: models.Config
    """
    return db.query(models.Config).filter(models.Config.name == config_name).first()

def get_api_key_db(db: Session, api_key: str):
    """Return the api_key in the database

    :param db: Database
    :type db: Session
    :param api_key: Value of the api_key
    :type api_key: str
    :return: APIKey
    :rtype: models.APIKeys
    """
    return db.query(models.APIKeys).filter(models.APIKeys.value == api_key).first()

def create_api_key_db(db: Session, api_key: schemas.APIKeysItem):
    """Create an API key in the database with a value of api_keys   

    :param db: Database
    :type db: Session
    :param api_key: Api_key to add
    :type api_key: schemas.APIKeysItem
    :return: Freshly created API Key
    :rtype: models.APIKeys
    """
    api_key_to_add = models.APIKeys(value=api_key.value, is_active=api_key.is_active)
    db.add(api_key_to_add)
    db.commit()
    db.refresh(api_key_to_add)
    return api_key_to_add

def get_api_keys_db(db: Session, skip: int = 0, limit: int = 100):
    """Get all the API keys in the Database

    :param db: Database
    :type db: Session
    :param skip: Skip the first skip numbers in the request, defaults to 0
    :type skip: int, optional
    :param limit: Max number of Api keys wanted, defaults to 100
    :type limit: int, optional
    :return: List of APIKeys
    :rtype: List[models.APIKeys]
    """
    return db.query(models.APIKeys).offset(skip).limit(limit).all()

def update_config(db: Session, config_name: str, new_value: int):
    """Update the value of config_name in the database with new_value

    :param db: Database
    :type db: Session
    :param config_name: Name of the config to change
    :type config_name: str
    :param new_value: New value wanted for the config
    :type new_value: int
    :return: the updated config
    :rtype: models.Config
    """
    conf = get_config(db, config_name)
    if(conf):
        conf.value = new_value
        db.commit()
    return conf
