import glob
import os
from importlib import reload

import boto
from moto import mock_s3

from aws_etl_tools import config
from aws_etl_tools.postgres_database import PostgresDatabase
from aws_etl_tools.redshift_database import RedshiftDatabase
from aws_etl_tools.redshift_ingest.ingestors import AuditedUpsertToPostgres
from . import settings


TEMP_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'tmp')
S3_TEST_BUCKET_NAME = settings.S3_TEST_BUCKET_NAME


s3_base_path = 's3://{}'.format(S3_TEST_BUCKET_NAME)
os.environ[config.S3_BASE_PATH_ENV_VAR_KEY] = s3_base_path
reload(config)


def clear_temp_directory():
    for test_file in glob.glob(TEMP_DIRECTORY + '/*.csv'):
        os.remove(test_file)


class BasicPostgres(PostgresDatabase):
    def __init__(self):
        self.credentials = settings.POSTGRES_TEST_CREDENTIALS


class BasicRedshift(RedshiftDatabase):
    def __init__(self):
        self.credentials = settings.REDSHIFT_TEST_CREDENTIALS


class BasicRedshiftButActuallyPostgres(RedshiftDatabase):
    ingestion_class = AuditedUpsertToPostgres

    def __init__(self):
        self.credentials = settings.REDSHIFT_TEST_CREDENTIALS