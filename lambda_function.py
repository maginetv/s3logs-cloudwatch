import urllib
import boto3
import re
import logging
import configparser
from datetime import datetime, timedelta

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

CONFIG = configparser.ConfigParser()
CONFIG.read_file(open('configuration.ini'))

CW_NAMESPACE = CONFIG.get('cloudwatch', 'namespace')
ROUND_TIMESTAMP_TO = CONFIG.getint('cloudwatch', 'round_timestamp_to_min') * 60
METRICS_CONFIG = [
    {
        'MetricNamePrefix': 'AllReqs',
        'FilterFunction': (lambda x: True),
    },
    {
        'MetricNamePrefix': 'RestGetObject',
        'FilterFunction': (lambda x: x['OPERATION'] == 'REST.GET.OBJECT'),
    },
    {
        'MetricNamePrefix': 'RestPutObject',
        'FilterFunction': (lambda x: x['OPERATION'] == 'REST.PUT.OBJECT'),
    },
    {
        'MetricNamePrefix': 'RestHeadObject',
        'FilterFunction': (lambda x: x['OPERATION'] == 'REST.HEAD.OBJECT'),
    },
    {
        'MetricNamePrefix': 'BatchDeleteObject',
        'FilterFunction': (lambda x: x['OPERATION'] == 'BATCH.DELETE.OBJECT'),
    },
    {
        'MetricNamePrefix': 'RestPostMultiObjectDelete',
        'FilterFunction': (lambda x:
                           x['OPERATION'] == 'REST.POST.MULTI_OBJECT_DELETE'),
    },
    {
        'MetricNamePrefix': 'RestGetObject_HTTP_2XX',
        'FilterFunction': (lambda x:
                           x['OPERATION'] == 'REST.GET.OBJECT' and
                           x['HTTP_STATUS'][0] == '2'),
    },
    {
        'MetricNamePrefix': 'RestGetObject_HTTP_4XX',
        'FilterFunction': (lambda x:
                           x['OPERATION'] == 'REST.GET.OBJECT' and
                           x['HTTP_STATUS'][0] == '4'),
    },
    {
        'MetricNamePrefix': 'RestGetObject_HTTP_5XX',
        'FilterFunction': (lambda x:
                           x['OPERATION'] == 'REST.GET.OBJECT' and
                           x['HTTP_STATUS'][0] == '5'),
    },
    {
        'MetricNamePrefix': 'RestPutObject_HTTP_2XX',
        'FilterFunction': (lambda x:
                           x['OPERATION'] == 'REST.PUT.OBJECT' and
                           x['HTTP_STATUS'][0] == '2'),
    },
    {
        'MetricNamePrefix': 'RestPutObject_HTTP_4XX',
        'FilterFunction': (lambda x:
                           x['OPERATION'] == 'REST.PUT.OBJECT' and
                           x['HTTP_STATUS'][0] == '4'),
    },
    {
        'MetricNamePrefix': 'RestPutObject_HTTP_5XX',
        'FilterFunction': (lambda x:
                           x['OPERATION'] == 'REST.PUT.OBJECT' and
                           x['HTTP_STATUS'][0] == '5'),
    }
]

for mc in METRICS_CONFIG:
    for x in ('RequestCount', 'TotalRequestTime', 'TurnAroundTime', 'ObjectSize'):
        if CONFIG.has_option('metrics_enabled', '{}_{}'.format(mc['MetricNamePrefix'], x)):
            mc[x] = CONFIG.getboolean(
                'metrics_enabled', '{}_{}'.format(mc['MetricNamePrefix'], x)
            )


def round_time(dt=None, round_to=60):
    if dt is None:
        dt = datetime.now()

    seconds = (dt - dt.min).seconds
    rounding = (seconds + round_to / 2) // round_to * round_to

    return dt + timedelta(
        0, rounding-seconds, -dt.microsecond
    )


class S3Log:
    def __init__(self, bucket, key):
        self.bucket = bucket
        self.key = key
        self.datapoints = []

        try:
            s3_client = boto3.client('s3')
            response = s3_client.get_object(Bucket=bucket, Key=key)
        except Exception as e:
            LOGGER.error(e)
            LOGGER.error(
                'Error getting object {} from bucket {}.'
                'Make sure they exist and your bucket is in '
                'the same region as this function.'.format(key, bucket))
            raise e

        s3_logline_regex = re.compile(
            r"""
            ^
            .+?\s                                # BUCKET_OWNER
            (?P<BUCKET_NAME>.+?)\s               # BUCKET_NAME
            \[
            (?P<TIME>.+?)                        # TIME
            \]\s
            .+?\s                                # REMOTE_IP
            .+?\s                                # REQUESTER
            .+?\s                                # REQUEST_ID
            (?P<OPERATION>.+?)\s                 # OPERATION
            .+?\s                                # KEY
            (?:"[^"]+?"|-)\s                     # REQUEST_URI
            (?P<HTTP_STATUS>(?:\d+|-))\s         # HTTP_STATUS
            .+?\s                                # ERROR_CODE
            (?P<BYTES_SENT>(?:\d+|-))\s          # BYTES_SENT
            (?P<OBJECT_SIZE>(?:\d+|-))\s         # OBJECT_SIZE
            (?P<TOTAL_TIME>(?:\d+|-))\s          # TOTAL_TIME
            (?P<TURN_AROUND_TIME>(?:\d+|-))\s    # TURN_AROUND_TIME
            (?:"[^"]+?"|-)\s                     # REFERRER
            (?:"[^"]+?"|-)\s                     # USER_AGENT
            .+?                                  # VERSION_ID
            """,
            re.X
        )

        for line in response['Body'].read().splitlines():
            match = s3_logline_regex.match(line.decode('utf-8'))
            dp = match.groupdict()
            dp['TIMESTAMP_LOWRES'] = round_time(
                datetime.strptime(dp['TIME'], '%d/%b/%Y:%X +0000'),
                round_to=ROUND_TIMESTAMP_TO,
            )
            dp['TIMESTAMP_LOWRES_ISO'] = dp['TIMESTAMP_LOWRES'].isoformat('T')
            self.datapoints.append(dp)

    def filtered_datapoints(self, filter_function):
        return filter(filter_function, self.datapoints)


class CloudWatchMetricsBuffer:
    def __init__(self, namespace, dimensions=[]):
        self.namespace = namespace
        self.metric_data = {}
        self.dimensions = dimensions
        self.requests_counter = 0
        self.cloudwatch_client = boto3.client('cloudwatch')

    def add_metric_datapoint(self, metric_name, timestamp_iso, unit, value):
        key = "".join([metric_name, timestamp_iso])
        value = float(value)
        if self.metric_data.get(key, None) is None:
            self.metric_data[key] = {
                'MetricName': metric_name,
                'Dimensions': self.dimensions,
                'Timestamp': datetime.strptime(
                    timestamp_iso,
                    '%Y-%m-%dT%H:%M:%S'),
                'StatisticValues': {
                    'SampleCount': 1,
                    'Sum': value,
                    'Minimum': value,
                    'Maximum': value,
                },
                'Unit': unit
            }
        else:
            prev = self.metric_data[key]['StatisticValues']
            prev['SampleCount'] += 1
            prev['Sum'] += value
            prev['Minimum'] = min(value, prev['Minimum'])
            prev['Maximum'] = max(value, prev['Maximum'])

    def flush(self):
        d = list(self.metric_data.values())
        # AWS Limit: Max 20 MetricDatum items in one PutMetricData request
        for x in range(0, len(d), 20):
            try:
                self.cloudwatch_client.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=d[x:x+20]
                )
            except Exception as e:
                # CloudWatch client retries with exponential backoff
                LOGGER.error('Error putting metric data. ERROR: {}'.format(e))
                raise e
            self.requests_counter += 1

    def get_requests_counter(self):
        return self.requests_counter

# --- MAIN ---


def lambda_handler(event, context):
    LOGGER.info("Received event: {}".format(event))
    logs_bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(
        event['Records'][0]['s3']['object']['key']
    )
    source_bucket = key.split('/', 1)[0]

    s3log = S3Log(logs_bucket, key)
    cwmb = CloudWatchMetricsBuffer(
        namespace=CW_NAMESPACE,
        dimensions=[
            {
                'Name': 'BucketName',
                'Value': source_bucket,
            },
        ]
    )

    for mc in METRICS_CONFIG:
        filtered_datapoints = s3log.filtered_datapoints(
            filter_function=mc['FilterFunction'])

        for datapoint in filtered_datapoints:
            timestamp_iso = datapoint['TIMESTAMP_LOWRES_ISO']
            if mc.get('RequestCount'):
                metric_name_suffix = 'RequestCount'
                value = 1
                cwmb.add_metric_datapoint(
                    metric_name="_".join(
                        [mc['MetricNamePrefix'], metric_name_suffix]
                    ),
                    timestamp_iso=timestamp_iso,
                    unit='Count',
                    value=value,
                )

            if (mc.get('TotalRequestTime') and datapoint['TOTAL_TIME'].isdigit()):
                metric_name_suffix = 'TotalRequestTime'
                value = int(datapoint['TOTAL_TIME'])
                cwmb.add_metric_datapoint(
                    metric_name="_".join(
                        [mc['MetricNamePrefix'], metric_name_suffix]
                    ),
                    timestamp_iso=timestamp_iso,
                    unit='Milliseconds',
                    value=value,
                )

            if (mc.get('TurnAroundTime') and datapoint['TURN_AROUND_TIME'].isdigit()):
                metric_name_suffix = 'TurnAroundTime'
                value = int(datapoint['TURN_AROUND_TIME'])
                cwmb.add_metric_datapoint(
                    metric_name="_".join(
                        [mc['MetricNamePrefix'], metric_name_suffix]
                    ),
                    timestamp_iso=timestamp_iso,
                    unit='Milliseconds',
                    value=value,
                )

            if (mc.get('ObjectSize') and datapoint['OBJECT_SIZE'].isdigit()):
                metric_name_suffix = 'ObjectSize'
                value = int(datapoint['OBJECT_SIZE'])
                cwmb.add_metric_datapoint(
                    metric_name="_".join(
                        [mc['MetricNamePrefix'], metric_name_suffix]
                    ),
                    timestamp_iso=timestamp_iso,
                    unit='Bytes',
                    value=value,
                )

    cwmb.flush()

    cwmb2 = CloudWatchMetricsBuffer(
        namespace='CloudWatch API calls',
        dimensions=[
            {
                'Name': 'FunctionName',
                'Value': 's3logs-cloudwatch',
            },
        ]
    )

    cwmb2.add_metric_datapoint(
        metric_name='PutMetricData_RequestsCount',
        timestamp_iso=datetime.utcnow().replace(
            second=0,
            microsecond=0
        ).isoformat('T'),
        unit='Count',
        value=float(cwmb.get_requests_counter()),
    )

    cwmb2.flush()

    return True
