from sqlalchemy import create_engine

from sqlhelp import update

from open_saturn.helper import config


def kill_workers():
    """ kills all workers
    """
    engine = create_engine(config()['db']['uri'])
    with engine.begin() as cn:
        update('rework.worker').values(
            kill=True, running=False, shutdown=True
        ).do(cn)


if __name__ == '__main__':
    kill_workers()
