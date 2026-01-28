import logging
import os
from datetime import datetime

LOG_DIR = 'logs'

def setup_logger(name, log_file=None):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    if log_file is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(LOG_DIR, f'{name}_{date_str}.log')
    else:
        log_file = os.path.join(LOG_DIR, log_file)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        return logger
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
