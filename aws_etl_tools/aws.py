import json
from urllib.request import urlopen

import boto
from boto.exception import BotoServerError, BotoClientError
from botocore.utils import METADATA_SECURITY_CREDENTIALS_URL

from aws_etl_tools import config


class AWS:
    '''this class is wrapping the boto s3_connection object with
        some extra attempts to make connecting as easy as possible.
        to override those, instantiate it like this:
        >> AWS(aws_access_key_id='brownie_recipe', secret_access_key='peanut_butter')
        aside from that, this class will look in the default boto config locations,
        and attempt a connection to s3 using the bucket defined as the config's base path.
        if that connection fails for any reason, then this class will hit amazon to
        request temporary credentials with a token based on the instance's IAM role.
        Either way, after initialization, this class is usable to connect to s3 and to
        build up a connection_string which is used primarily in Redshift commands like
        `COPY` from s3 and `UNLOAD` to s3.
    '''

    def __init__(self, **kwargs):
        try:
            self._connect_with_permanent_credentials(**kwargs)
            testable_bucket_name = config.S3_BASE_PATH.replace('s3://', '').split('/')[0]
            self.s3_connection().get_bucket(testable_bucket_name)
        except (BotoServerError, BotoClientError):
            self._connect_with_temporary_credentials()

    def connection_string(self):
        aws_credential_string = 'aws_access_key_id=%s;aws_secret_access_key=%s' % (
            self.key, self.secret)
        if self.token is not None:
            aws_credential_string += ';token=%s' % self.token
        return aws_credential_string

    def s3_connection(self):
        return boto.connect_s3(aws_access_key_id=self.key,
                               aws_secret_access_key=self.secret,
                               security_token=self.token)

    def _connect_with_permanent_credentials(self, **kwargs):
        '''creates a connection to s3 through boto using a set key and secret
            that is either passed in explicitly, set through environment
            variables in config, or set in a boto configuration file in the
            default location'''
        possibly_valid_key = kwargs.get('aws_access_key_id', config.AWS_ACCESS_KEY_ID)
        possibly_valid_secret = kwargs.get('aws_secret_access_key', config.AWS_SECRET_ACCESS_KEY)
        local_aws_connection = boto.connect_s3(
            aws_access_key_id=possibly_valid_key,
            aws_secret_access_key=possibly_valid_secret,
            **kwargs
        )
        self.key = local_aws_connection.aws_access_key_id
        self.secret = local_aws_connection.aws_secret_access_key
        self.token = None

    def _connect_with_temporary_credentials(self):
        credentials_from_iam_role = self._request_temporary_credentials()
        self.key = credentials_from_iam_role['AccessKeyId']
        self.secret = credentials_from_iam_role['SecretAccessKey']
        self.token = credentials_from_iam_role['Token']

    def _request_temporary_credentials(self):
        aws_iam_base_url = METADATA_SECURITY_CREDENTIALS_URL
        iam_role_name = urlopen(aws_iam_base_url).read().decode()
        aws_iam_creds_url = aws_iam_base_url + iam_role_name
        creds_dictionary = json.loads(
            urlopen(aws_iam_creds_url).read().decode())
        return creds_dictionary