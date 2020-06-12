import logging


def initialize_logger():
    logger = logging.getLogger('debugger')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(filename)s:%(lineno)s - ' + '%(levelname)s --- %(message)s '
                                  , datefmt='%Y-%m-%d %H:%M:%S')

    # create error file handler and set level to error
    handler = logging.FileHandler("logs/error.log", "w")
    handler.setLevel(logging.ERROR)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create debug file handler and set level to debug
    handler = logging.FileHandler("logs/all.log", "w")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
