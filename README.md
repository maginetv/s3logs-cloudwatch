# s3logs-cloudwatch

AWS Lambda function to parse S3 server log files and export
metrics to AWS CloudWatch.

- [Description](#description)
- [Extra S3 Metrics available](#metrics-available)
- [Deployment](#deployment)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)

<a name="description"/>
## Description

This AWS Lambda function will analyze and aggregate your S3 Server Access log
files and graph extra metrics in AWS CloudWatch.

**NOTE:** AWS introduced S3 request metrics at re:Invent 2016. This makes parts of below README outdated as of December 2016 and it might not be the most optimal way of achieving your goals. Before reading further please check out AWS documentation: [S3 Request Metrics](http://docs.aws.amazon.com/AmazonS3/latest/dev/cloudwatch-monitoring.html). There are still extra, more specific metrics provided by s3logs-cloudwatch that the "official way" does not provide.

![metrics_example](https://cloud.githubusercontent.com/assets/1117361/17244194/ee594280-5580-11e6-8879-7acd3f6519b8.png)

AWS S3 is a managed storage service. The only metrics available
in AWS CloudWatch for S3 are `NumberOfObjects` and `BucketSizeBytes`. In order
to understand your S3 usage better you need to do some extra work. Reasons can
be multiple: understanding your AWS bill, getting better idea of how your
deployed applications use S3, access auditing, security, performance
considerations or proactive monitoring because you love metrics.

AWS offers server access logging to track requests for access to your bucket.
This is a feature that is disabled by default, but you can enable it free
of charge (you will be charged for storage used for storing files and data
transfer for access to delivered log files).

To find out more about Server Access Logging feature of S3, head over to [Server
Access Logging](http://docs.aws.amazon.com/AmazonS3/latest/dev/ServerLogs.html)
section in Amazon Simple Storage Service Developer Guide.

<a name="metrics-available"/>
## Extra S3 Metrics available

Custom metrics are sent to AWS CloudWatch under the namespace `S3 Logs`.
You can choose a different namespace name in `configuration.ini` file. Each
metric has a dimension `BucketName` in case you would like to enable graphing
requests for multiple buckets.

Metrics enabled by default are listed below.
To enable or disable specific metric edit `configuration.ini` file.

| Metric name                                        | Enabled (default) |
|:---------------------------------------------------|:-----------------:|
|AllReqs_RequestCount                                | on
|AllReqs_TotalRequestTime                            | off
|AllReqs_TurnAroundTime                              | off
|RestGetObject_RequestCount                          | on
|RestGetObject_TotalRequestTime                      | on
|RestGetObject_TurnAroundTime                        | on
|RestPutObject_RequestCount                          | on
|RestPutObject_TotalRequestTime                      | on
|RestPutObject_TurnAroundTime                        | on
|RestHeadObject_RequestCount                         | on
|RestHeadObject_TotalRequestTime                     | on
|RestHeadObject_TurnAroundTime                       | off
|BatchDeleteObject_RequestCount                      | on
|BatchDeleteObject_TotalRequestTime                  | off
|BatchDeleteObject_TurnAroundTime                    | off
|RestPostMultiObjectDelete_RequestCount              | on
|RestPostMultiObjectDelete_TotalRequestTime          | off
|RestPostMultiObjectDelete_TurnAroundTime            | off
|RestGetObject_HTTP_2XX_RequestCount                 | on
|RestGetObject_HTTP_2XX_TotalRequestTime             | off
|RestGetObject_HTTP_2XX_TurnAroundTime               | off
|RestGetObject_HTTP_2XX_ObjectSize                   | on
|RestGetObject_HTTP_4XX_RequestCount                 | on
|RestGetObject_HTTP_4XX_TotalRequestTime             | off
|RestGetObject_HTTP_4XX_TurnAroundTime               | off
|RestGetObject_HTTP_5XX_RequestCount                 | on
|RestGetObject_HTTP_5XX_TotalRequestTime             | off
|RestGetObject_HTTP_5XX_TurnAroundTime               | off
|RestPutObject_HTTP_2XX_RequestCount                 | on
|RestPutObject_HTTP_2XX_TotalRequestTime             | off
|RestPutObject_HTTP_2XX_TurnAroundTime               | off
|RestPutObject_HTTP_2XX_ObjectSize                   | on
|RestPutObject_HTTP_4XX_RequestCount                 | on
|RestPutObject_HTTP_4XX_TotalRequestTime             | off
|RestPutObject_HTTP_4XX_TurnAroundTime               | off
|RestPutObject_HTTP_5XX_RequestCount                 | on
|RestPutObject_HTTP_5XX_TotalRequestTime             | off
|RestPutObject_HTTP_5XX_TurnAroundTime               | off

**RequestCount**

Self explanatory hopefully. Amount of requests.

**TotalRequestTime**

The number of milliseconds the request was in flight from the server's
perspective. This value is measured from the time your request is received to
the time that the last byte of the response is sent. Measurements made from the
client's perspective might be longer due to network latency.

**TurnAroundTime**

The number of milliseconds that Amazon S3 spent processing your request. This
value is measured from the time the last byte of your request was received until
the time the first byte of the response was sent.

For more detailed information, head over to [Server Access Log
Format](http://docs.aws.amazon.com/AmazonS3/latest/dev/LogFormat.html) section
in Amazon Simple Storage Developer Guide.

**ObjectSize**

The total size of the object in question.

<a name="deployment"/>
## Deployment

Follow below steps to enable CloudWatch metrics for bucket
`com-companyname-mybucket`.

1. Create a new S3 bucket for storing your S3 logs, for example
`com-companyname-s3logs`

2. Enable logging on `com-companyname-mybucket` bucket
   
   For information on how to enable bucket logging, see [Enabling Logging
   Using the Console]
   (http://docs.aws.amazon.com/AmazonS3/latest/dev/enable-logging-console.html).
   
   IMPORTANT: Set `com-companyname-s3logs` as **Target Bucket** for log
   objects. Specify `com-companyname-mybucket/` as **Target
   Prefix**. **Target Prefix** value must end with a `/` for s3logs-cloudwatch
   Lambda function to properly set BucketName dimension in exported
   CloudWatch metrics

   ![bucket_setup](https://cloud.githubusercontent.com/assets/1117361/17244192/ee581efa-5580-11e6-9b23-5e86783a73a8.png)

3. Clone this GitHub repository so you have it locally and prepare deployment
package. Upload deployment package to S3.

   ```bash
   $ git clone git@github.com:maginetv/s3logs-cloudwatch.git
   $ cd s3logs-cloudwatch/
   ```
   
   Edit `configuration.ini` file if you would like to adjust the settings or
   change which metrics will be exported to CloudWatch.
   Then zip the files and put resulting zip somewhere on S3.

   ```bash
   $ zip s3logs-cloudwatch.zip lambda_function.py configuration.ini
   $ s3cmd cp s3logs-cloudwatch.zip s3://com-companyname-packages/lambda/s3logs-cloudwatch.zip
   ```
   
4. Use provided CloudFormation template to deploy s3logs-cloudwatch AWS Lambda
function and IAM role that is required to run it.
   
   Go to CloudFormation in AWS Console and create the stack using provided
   CloudFormation template `cloudformation/cloudformation-deploy.json`.

   ![cloudformation_setup](https://cloud.githubusercontent.com/assets/1117361/17244195/ee5d3750-5580-11e6-955e-c8cdf1adde76.png)

5. Last step is creating and enabling triggers (event sources) for deployed
Lambda function. Head over to AWS Lambda in AWS console and find
`s3logs-cloudwatch` function in functions list. Deployed function is supposed
to be run every time a new S3 log file is delivered to `com-companyname-s3logs`
bucket. Picture below shows the configuration that has to be in place for the
trigger to work:

   ![lambda_trigger](https://cloud.githubusercontent.com/assets/1117361/17244193/ee58459c-5580-11e6-9241-90f8aafc2636.png)

   If you need to enable s3logs-cloudwatch to graph S3 metrics from multiple S3
   buckets just add another trigger (with different prefix/suffix setting).

6. That's it. Your new Cloudwatch metrics will start appearing soon.

<a name="faq"/>
## FAQ

**Q: I don't see metrics in Cloudwatch from the last hour, why?**

A: AWS delivers log files to your logs bucket every once in a while. It's log
file delivery that triggers the processing and exporting metrics to CloudWatch.
Log files are usually delivered every 1 hour and that's when CloudWatch graphs
for s3logs-cloudwatch metrics are updated.

**Q: How much does it cost to run this function?**

A: As with everything on AWS. You pay for what you use. The monthly price of
deploying this function on your AWS account will depend on: the volume of log
files that need to be processed, amount of resources that you assign to
s3logs-cloudwatch Lambda function and granularity od data aggregation
(`round_timestamp_to_min` setting in `configuration.ini` file).
s3logs-cloudwatch aims to do everything in most cost effective way possible.

**Q: My logs bucket (`com-companyname-s3logs`) is growing really big, I do not
need my S3 logs to be stored for such a long time because it's expensive.**

A: Enable S3 lifecycle rules for `com-companyname-s3logs` bucket. You can
configure `com-companyname-s3logs` bucket to delete log files permanently after
certain period (for example 1 or 7 days). Check [Object Lifecycle Management]
(http://docs.aws.amazon.com/AmazonS3/latest/dev/object-lifecycle-mgmt.html) in
Amazon S3 Developer Guide.


<a name="contributing"/>
## Contributing

Pull requests are very welcome if you feel like you would like to improve
or add any functionality. In order to contribute:

- Fork this repository on GitHub
- Create your own topic branch
- Once finished, submit a pull request

<a name="license"/>
## License

Released under the [Apache 2.0 license](LICENSE).

```
Copyright 2016 Magine AB

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

<a name="author"/>
## Author

Michal Gasek (michal.gasek at magine/com)
