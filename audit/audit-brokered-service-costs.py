#!/usr/bin/env python3

import argparse
import functools
import json
import subprocess


# Prefix for all production Elasticsearch domains.
ES_PROD_DOMAIN_PREFIX="cg-broker-prd-"

# As defined by AWS with their pricing calculator at https://calculator.aws/
HOURS_PER_MONTH = 730

ES_PRICING_INFO = {
    "storage": {
        "gp2": 0.162
    },
    "instance_classes": {
        "c5.large.elasticsearch": 0.15,
        "c5.xlarge.elasticsearch": 0.301,
        "t2.small.elasticsearch": 0.043,
    }
}

RDS_PRICING_INFO = {
    "mysql": {
        "storage": {
            "multi_az": 0.276,
            "single": 0.138
        },
        "instance_classes": {
            "db.m6g.large": {
                "multi_az": 0.362,
                "single": 0.181
            },
            "db.m6g.xlarge": {
                "multi_az": 0.723,
                "single": 0.362
            },
            "db.m6g.2xlarge": {
                "multi_az": 1.446,
                "single": 0.723
            },
            "db.m6g.4xlarge": {
                "multi_az": 2.893,
                "single": 1.446
            },
            "db.m6g.8xlarge": {
                "multi_az": 5.786,
                "single": 2.893
            },
            "db.m6g.12xlarge": {
                "multi_az": 8.678,
                "single": 4.339
            },
            "db.m6g.16xlarge": {
                "multi_az": 11.571,
                "single": 5.786
            },
            "db.m5.large": {
                "multi_az": 0.41,
                "single": 0.205
            },
            "db.m5.xlarge": {
                "multi_az": 0.82,
                "single": 0.41
            },
            "db.m5.2xlarge": {
                "multi_az": 1.64,
                "single": 0.82
            },
            "db.m5.4xlarge": {
                "multi_az": 3.28,
                "single": 1.64
            },
            "db.m5.8xlarge": {
                "multi_az": 6.55,
                "single": 3.27
            },
            "db.m5.12xlarge": {
                "multi_az": 9.84,
                "single": 4.92
            },
            "db.m5.16xlarge": {
                "multi_az": 13.10,
                "single": 6.55
            },
            "db.m5.24xlarge": {
                "multi_az": 19.68,
                "single": 9.84
            },
            "db.r6g.large": {
                "multi_az": 0.517,
                "single": 0.259
            },
            "db.r6g.xlarge": {
                "multi_az": 1.034,
                "single": 0.517
            },
            "db.r6g.2xlarge": {
                "multi_az": 2.068,
                "single": 1.034
            },
            "db.r6g.4xlarge": {
                "multi_az": 4.137,
                "single": 2.068
            },
            "db.r6g.8xlarge": {
                "multi_az": 8.274,
                "single": 4.137
            },
            "db.r6g.12xlarge": {
                "multi_az": 12.41,
                "single": 6.205
            },
            "db.r6g.16xlarge": {
                "multi_az": 16.547,
                "single": 8.274
            },
            "db.r5.8xlarge": {
                "multi_az": 9.25,
                "single": 4.62
            },
            "db.r5.16xlarge": {
                "multi_az": 18.49,
                "single": 9.25
            },
            "db.t2.micro": {
                "multi_az": 0.04,
                "single": 0.02
            },
            "db.t2.small": {
                "multi_az": 0.082,
                "single": 0.041
            },
            "db.t2.medium": {
                "multi_az": 0.162,
                "single": 0.081
            },
            "db.t2.large": {
                "multi_az": 0.324,
                "single": 0.162
            },
            "db.t2.xlarge": {
                "multi_az": 0.648,
                "single": 0.324
            },
            "db.t2.2xlarge": {
                "multi_az": 1.296,
                "single": 0.648
            },
            "db.m4.large": {
                "multi_az": 0.42,
                "single": 0.21
            },
            "db.m4.xlarge": {
                "multi_az": 0.84,
                "single": 0.42
            },
            "db.m4.2xlarge": {
                "multi_az": 1.68,
                "single": 0.84
            },
            "db.m4.4xlarge": {
                "multi_az": 3.36,
                "single": 1.68
            },
            "db.m4.10xlarge": {
                "multi_az": 8.40,
                "single": 4.20
            },
            "db.m4.16xlarge": {
                "multi_az": 13.44,
                "single": 6.72
            },
            "db.m3.medium": {
                "multi_az": 0.22,
                "single": 0.11
            },
            "db.m3.large": {
                "multi_az": 0.44,
                "single": 0.22
            },
            "db.m3.xlarge": {
                "multi_az": 0.85,
                "single": 0.425
            },
            "db.m3.2xlarge": {
                "multi_az": 1.71,
                "single": 0.855
            },
            "db.m1.small": {
                "multi_az": 0.13,
                "single": 0.065
            },
            "db.m1.medium": {
                "multi_az": 0.27,
                "single": 0.135
            },
            "db.m1.large": {
                "multi_az": 0.53,
                "single": 0.265
            },
            "db.m1.xlarge": {
                "multi_az": 1.07,
                "single": 0.535
            },
            "db.m2.xlarge": {
                "multi_az": 0.75,
                "single": 0.375
            },
            "db.m2.2xlarge": {
                "multi_az": 1.51,
                "single": 0.755
            },
            "db.m2.4xlarge": {
                "multi_az": 3.02,
                "single": 1.51
            },
            "db.r4.large": {
                "multi_az": 0.578,
                "single": 0.289
            },
            "db.r4.xlarge": {
                "multi_az": 1.156,
                "single": 0.578
            },
            "db.r4.2xlarge": {
                "multi_az": 2.312,
                "single": 1.156
            },
            "db.r4.4xlarge": {
                "multi_az": 4.624,
                "single": 2.312
            },
            "db.r4.8xlarge": {
                "multi_az": 9.248,
                "single": 4.624
            },
            "db.r4.16xlarge": {
                "multi_az": 18.496,
                "single": 9.248
            },
            "db.r3.large": {
                "multi_az": 0.578,
                "single": 0.289
            },
            "db.r3.xlarge": {
                "multi_az": 1.138,
                "single": 0.569
            },
            "db.r3.2xlarge": {
                "multi_az": 2.268,
                "single": 1.134
            },
            "db.r3.4xlarge": {
                "multi_az": 4.536,
                "single": 2.268
            },
            "db.r3.8xlarge": {
                "multi_az": 9.072,
                "single": 4.536
            }
        }
    },
    "postgres": {
        "storage": {
            "multi_az": 0.276,
            "single": 0.138
        },
        "instance_classes": {
            "db.t3.micro": {
                "multi_az": 0.043,
                "single": 0.022
            },
            "db.t3.small": {
                "multi_az": 0.09,
                "single": 0.04
            },
            "db.t3.medium": {
                "multi_az": 0.17,
                "single": 0.09
            },
            "db.t3.large": {
                "multi_az": 0.35,
                "single": 0.17
            },
            "db.t3.xlarge": {
                "multi_az": 0.7,
                "single": 0.35
            },
            "db.t3.2xlarge": {
                "multi_az": 1.39,
                "single": 0.7
            },
            "db.m6g.large": {
                "multi_az": 0.372,
                "single": 0.186
            },
            "db.m6g.xlarge": {
                "multi_az": 0.743,
                "single": 0.372
            },
            "db.m6g.2xlarge": {
                "multi_az": 1.486,
                "single": 0.743
            },
            "db.m6g.4xlarge": {
                "multi_az": 2.973,
                "single": 1.486
            },
            "db.m6g.8xlarge": {
                "multi_az": 5.946,
                "single": 2.973
            },
            "db.m6g.12xlarge": {
                "multi_az": 8.918,
                "single": 4.459
            },
            "db.m6g.16xlarge": {
                "multi_az": 11.891,
                "single": 5.946
            },
            "db.m5.large": {
                "multi_az": 0.43,
                "single": 0.21
            },
            "db.m5.xlarge": {
                "multi_az": 0.85,
                "single": 0.43
            },
            "db.m5.2xlarge": {
                "multi_az": 1.7,
                "single": 0.85
            },
            "db.m5.4xlarge": {
                "multi_az": 3.41,
                "single": 1.7
            },
            "db.m5.8xlarge": {
                "multi_az": 6.82,
                "single": 3.41
            },
            "db.m5.12xlarge": {
                "multi_az": 10.23,
                "single": 5.11
            },
            "db.m5.16xlarge": {
                "multi_az": 13.63,
                "single": 6.82
            },
            "db.m5.24xlarge": {
                "multi_az": 20.45,
                "single": 10.23
            },
            "db.r6g.large": {
                "multi_az": 0.54,
                "single": 0.27
            },
            "db.r6g.xlarge": {
                "multi_az": 1.079,
                "single": 0.54
            },
            "db.r6g.2xlarge": {
                "multi_az": 2.158,
                "single": 1.079
            },
            "db.r6g.4xlarge": {
                "multi_az": 4.317,
                "single": 2.158
            },
            "db.r6g.8xlarge": {
                "multi_az": 8.634,
                "single": 4.317
            },
            "db.r6g.12xlarge": {
                "multi_az": 12.95,
                "single": 6.475
            },
            "db.r6g.16xlarge": {
                "multi_az": 17.267,
                "single": 8.634
            },
            "db.r5.large": {
                "multi_az": 0.6,
                "single": 0.3
            },
            "db.r5.xlarge": {
                "multi_az": 1.2,
                "single": 0.6
            },
            "db.r5.2xlarge": {
                "multi_az": 2.41,
                "single": 1.2
            },
            "db.r5.4xlarge": {
                "multi_az": 4.82,
                "single": 2.41
            },
            "db.r5.8xlarge": {
                "multi_az": 9.63,
                "single": 4.82
            },
            "db.r5.12xlarge": {
                "multi_az": 14.45,
                "single": 7.22
            },
            "db.r5.16xlarge": {
                "multi_az": 19.26,
                "single": 9.63
            },
            "db.r5.24xlarge": {
                "multi_az": 28.9,
                "single": 14.45
            },
            "db.t2.micro": {
                "multi_az": 0.042,
                "single": 0.021
            },
            "db.t2.small": {
                "multi_az": 0.086,
                "single": 0.043
            },
            "db.t2.medium": {
                "multi_az": 0.174,
                "single": 0.087
            },
            "db.t2.large": {
                "multi_az": 0.348,
                "single": 0.174
            },
            "db.t2.xlarge": {
                "multi_az": 0.696,
                "single": 0.348
            },
            "db.t2.2xlarge": {
                "multi_az": 1.392,
                "single": 0.696
            },
            "db.m4.large": {
                "multi_az": 0.436,
                "single": 0.218
            },
            "db.m4.xlarge": {
                "multi_az": 0.872,
                "single": 0.436
            },
            "db.m4.2xlarge": {
                "multi_az": 1.744,
                "single": 0.872
            },
            "db.m4.4xlarge": {
                "multi_az": 3.488,
                "single": 1.744
            },
            "db.m4.10xlarge": {
                "multi_az": 8.72,
                "single": 4.36
            },
            "db.m4.16xlarge": {
                "multi_az": 13.952,
                "single": 6.976
            },
            "db.m3.medium": {
                "multi_az": 0.23,
                "single": 0.115
            },
            "db.m3.large": {
                "multi_az": 0.47,
                "single": 0.235
            },
            "db.m3.xlarge": {
                "multi_az": 0.89,
                "single": 0.445
            },
            "db.m3.2xlarge": {
                "multi_az": 1.78,
                "single": 0.89
            },
            "db.m1.small": {
                "multi_az": 0.14,
                "single": 0.07
            },
            "db.m1.medium": {
                "multi_az": 0.28,
                "single": 0.14
            },
            "db.m1.large": {
                "multi_az": 0.56,
                "single": 0.28
            },
            "db.m1.xlarge": {
                "multi_az": 1.12,
                "single": 0.56
            },
            "db.m2.xlarge": {
                "multi_az": 0.79,
                "single": 0.395
            },
            "db.m2.2xlarge": {
                "multi_az": 1.58,
                "single": 0.79
            },
            "db.m2.4xlarge": {
                "multi_az": 3.16,
                "single": 1.58
            },
            "db.r4.large": {
                "multi_az": 0.602,
                "single": 0.301
            },
            "db.r4.xlarge": {
                "multi_az": 1.204,
                "single": 0.602
            },
            "db.r4.2xlarge": {
                "multi_az": 2.408,
                "single": 1.204
            },
            "db.r4.4xlarge": {
                "multi_az": 4.816,
                "single": 2.408
            },
            "db.r4.8xlarge": {
                "multi_az": 9.632,
                "single": 4.816
            },
            "db.r4.16xlarge": {
                "multi_az": 19.264,
                "single": 9.632
            },
            "db.r3.large": {
                "multi_az": 0.602,
                "single": 0.301
            },
            "db.r3.xlarge": {
                "multi_az": 1.198,
                "single": 0.599
            },
            "db.r3.2xlarge": {
                "multi_az": 2.388,
                "single": 1.194
            },
            "db.r3.4xlarge": {
                "multi_az": 4.776,
                "single": 2.388
            },
            "db.r3.8xlarge": {
                "multi_az": 9.552,
                "single": 4.776
            }
        }
    }
}

REDIS_PRICING_INFO = {
    "cache.t2.micro": 0.019,
    "cache.t3.micro": 0.02,
    "cache.t3.small": 0.04,
}


def parse_args():
    """
    Parses command line arguments to run the script.
    """

    parser = argparse.ArgumentParser(
        description="Processes AWS API data of brokered services for cost analysis."
    )

    parser.add_argument(
        "aws_service",
        choices=["es", "rds", "redis", "aws-resource-tags"],
        help="The AWS service to analyze"
    )
    parser.add_argument(
        "json_file",
        help="The JSON output to process"
    )
    parser.add_argument(
        "--limit",
        default=0,
        help="Limits the amount of records processed to LIMIT"
    )
    return parser.parse_args()


@functools.cache
def get_cf_entity_name(entity, guid):
    """
    Retrieves the name of a CF entity from a GUID.
    """

    cf_json = subprocess.check_output(
        ["cf", "curl", "/v3/" + entity + "/" + guid],
        universal_newlines=True
    )
    cf_data = json.loads(cf_json)

    return cf_data.get("name", "N/A")


def parse_aws_resource_tags(json_file, limit):
    """
    Processes tags for a AWS resources and retrieves their associated Cloud
    Foundry values.
    """

    def parse_aws_resource_name(aws_resource_arn):
        """
        Parses out the AWS resource name from an AWS ARN.  Accounts for at least
        Elasticsearch and ElastiCache ARN formats.
        """

        parts = aws_resource_arn.split(":")
        name_part = parts[-1].split("/")[-1]

        return name_part

    count = 0
    tag_data = json.load(open(json_file))

    print("AWS Resource Name,Instance GUID,Space GUID,Organization GUID,Instance Name,Space Name,Organization Name")

    for resource in tag_data["aws_resource_tags"]:
        # Retrieve all of the tags associated with the resource.
        tags = { tag.get("Key"): tag.get("Value") for tag in resource["TagList"] }

        # If we set a processing limit and we haven't skipped, check to see if
        # we should stop.
        if limit > 0 and count >= limit:
            break

        # Check if the instance has the appropriate CF metadata associated with
        # it and if not, default to N/A values.
        if "Instance GUID" in tags:
            instance_guid = tags["Instance GUID"]
            instance_name = get_cf_entity_name(
                "service_instances",
                tags["Instance GUID"]
            )
        else:
            instance_guid = "N/A"
            instance_name = "N/A"

        if "Organization GUID" in tags:
            org_guid = tags["Organization GUID"]
            org_name = get_cf_entity_name(
                "organizations",
                tags["Organization GUID"]
            )
        else:
            org_guid = "N/A"
            org_name = "N/A"

        if "Space GUID" in tags:
            space_guid = tags["Space GUID"]
            space_name = get_cf_entity_name(
                "spaces",
                tags["Space GUID"]
            )
        else:
            space_guid = "N/A"
            space_name = "N/A"

        output = "{aws_resource_name},{instance_guid},{space_guid},{org_guid},{instance_name},{space_name},{org_name}".format(
            aws_resource_name=parse_aws_resource_name(resource["arn"]),
            instance_guid=instance_guid,
            space_guid=space_guid,
            org_guid=org_guid,
            instance_name=instance_name,
            space_name=space_name,
            org_name=org_name
        )

        print(output)
        count += 1


def analyze_es(json_file, limit):
    """
    Analyzes a JSON file containing AWS Elasticsearch domain information.
    """

    def calculate_monthly_cost(num_data_instances, data_instance_class_price, num_master_instances, master_instance_class_price, storage_size, storage_price):
        """
        Calculates the monthly cost of an Elasticsearch domain.  Note that this
        is a rough estimate based on AWS' pricing formula for Elasticsearch:

        (num_data_instances * data_instance_class_price * HOURS_PER_MONTH) +
        (num_master_instances * master_instance_class_price * HOURS_PER_MONTH) +
        (storage_size * storage_price * num_data_instances)

        Returns the value formatted as a string, rounded to 2 decimal places.
        """

        estimate = (int(num_data_instances) * data_instance_class_price * HOURS_PER_MONTH) + (int(num_master_instances) * master_instance_class_price * HOURS_PER_MONTH) + (int(storage_size) * storage_price * int(num_data_instances))
        return "{estimate:.2f}".format(estimate=estimate)

    count = 0
    es_domain_data = json.load(open(json_file))

    print("Domain Name,Data Instance Class,Num Data Instances,Data Instance Class Price Per Hour,Master Instance Class,Num Master Instances,Master Instance Class Price per Hour,Data Storage Size,Storage Type,Storage Price per GB/Month,Total Monthly Estimate")

    for es_domain in es_domain_data["DomainStatusList"]:
        # If we set a processing limit and we haven't skipped, check to see if
        # we should stop.
        if limit > 0 and count >= limit:
            break

        # Check for the presence of master instances.
        if es_domain["ElasticsearchClusterConfig"]["DedicatedMasterEnabled"]:
            master_instance_class=es_domain["ElasticsearchClusterConfig"]["DedicatedMasterType"]
            num_master_instances=es_domain["ElasticsearchClusterConfig"]["DedicatedMasterCount"]
            master_instance_class_price = ES_PRICING_INFO["instance_classes"][master_instance_class]
        else:
            master_instance_class = "N/A"
            num_master_instances = 0
            master_instance_class_price = 0

        output = "{domain_name},{data_instance_class},{num_data_instances},{data_instance_class_price},{master_instance_class},{num_master_instances},{master_instance_class_price},{data_storage_size},{storage_type},{storage_price},{total_monthly_estimate}".format(
            domain_name=es_domain["DomainName"],
            data_instance_class=es_domain["ElasticsearchClusterConfig"]["InstanceType"],
            num_data_instances=es_domain["ElasticsearchClusterConfig"]["InstanceCount"],
            data_instance_class_price=ES_PRICING_INFO["instance_classes"][es_domain["ElasticsearchClusterConfig"]["InstanceType"]],
            master_instance_class=master_instance_class,
            num_master_instances=num_master_instances,
            master_instance_class_price=master_instance_class_price,
            data_storage_size=es_domain["EBSOptions"]["VolumeSize"],
            storage_type=es_domain["EBSOptions"]["VolumeType"],
            storage_price=ES_PRICING_INFO["storage"]["gp2"],
            total_monthly_estimate=calculate_monthly_cost(
                es_domain["ElasticsearchClusterConfig"]["InstanceCount"],
                ES_PRICING_INFO["instance_classes"][es_domain["ElasticsearchClusterConfig"]["InstanceType"]],
                num_master_instances,
                master_instance_class_price,
                es_domain["EBSOptions"]["VolumeSize"],
                ES_PRICING_INFO["storage"]["gp2"],
            )
        )

        print(output)
        count += 1


def analyze_rds(json_file, limit):
    """
    Analyzes a JSON file containing AWS RDS instance information.
    """

    def calculate_monthly_cost(instance_class_price, storage_price, storage_size):
        """
        Calculates the monthly cost of an RDS instance.  Note that this is a
        rough estimate based on AWS' pricing formula for RDS, and the instance
        class price factors in whether or not an instance is set with MultiAZ:

        (instance_class_price * HOURS_PER_MONTH) + (storage_size * storage_price)

        Returns the value formatted as a string, rounded to 2 decimal places.
        """

        estimate = (instance_class_price * HOURS_PER_MONTH) + (storage_size * storage_price)
        return "{estimate:.2f}".format(estimate=estimate)

    count = 0
    rds_instance_data = json.load(open(json_file))

    print("Instance Class,Engine,MultiAZ,Storage Type,Storage Size,Instance GUID,Space GUID,Organization GUID,Space Name,Organization Name,Instance Class Price per Hour,Storage Price per GB/Month,Total Monthly Estimate")

    for db_instance in rds_instance_data["DBInstances"]:
        # Retrieve all of the tags associated with the instance.
        tags = { tag.get("Key"): tag.get("Value") for tag in db_instance["TagList"] }

        # Check if the instance has the appropriate CF metadata associated with
        # it and if not, skip it.  The remaining instances may not always
        # represent a customer instance, but it's a close enough estimate for
        # our purposes.
        # If we set a processing limit and we haven't skipped, check to see if
        # we should stop.
        if "Instance GUID" not in tags:
            continue
        elif limit > 0 and count >= limit:
            break

        org_name = get_cf_entity_name(
            "organizations",
            tags["Organization GUID"]
        )

        space_name = get_cf_entity_name(
            "spaces",
            tags["Space GUID"]
        )

        if db_instance["MultiAZ"]:
            instance_class_price = RDS_PRICING_INFO[db_instance["Engine"]]["instance_classes"][db_instance["DBInstanceClass"]]["multi_az"]
            storage_price = RDS_PRICING_INFO[db_instance["Engine"]]["storage"]["multi_az"]
            is_multi_az = "Yes"
        else:
            instance_class_price = RDS_PRICING_INFO[db_instance["Engine"]]["instance_classes"][db_instance["DBInstanceClass"]]["single"]
            storage_price = RDS_PRICING_INFO[db_instance["Engine"]]["storage"]["single"]
            is_multi_az = "No"

        output = "{instance_class},{engine},{multi_az},{storage_type},{storage_size},{instance_guid},{space_guid},{org_guid},{space_name},{org_name},{instance_class_price},{storage_price},{total_monthly_estimate}".format(
            instance_class=db_instance["DBInstanceClass"],
            engine=db_instance["Engine"],
            multi_az=is_multi_az,
            storage_type=db_instance["StorageType"],
            storage_size=db_instance["AllocatedStorage"],
            instance_guid=tags["Instance GUID"],
            space_guid=tags["Space GUID"],
            org_guid=tags["Organization GUID"],
            space_name=space_name,
            org_name=org_name,
            instance_class_price=instance_class_price,
            storage_price=storage_price,
            total_monthly_estimate=calculate_monthly_cost(
                instance_class_price,
                storage_price,
                db_instance["AllocatedStorage"]
            )
        )

        print(output)
        count += 1


def analyze_redis(json_file, limit):
    """
    Analyzes a JSON file containing AWS ElastiCache Redis cluster information.
    """

    def calculate_monthly_cost(num_instances, instance_class_price):
        """
        Calculates the monthly cost of a Redis cluster.  Note that this
        is a rough estimate based on AWS' pricing formula for ElastiCache:

        Actual price for (3 instances) Memcached Memory optimized cache r4.16xlarge OnDemand (Hourly): 3 instance(s) x 8.73600000 USD hourly = 26.208 USD

        3 instance(s) x 8.73600000 USD hourly x 730 hours in a month = 19,131.84 USD

        num_instances * instance_class_price * HOURS_PER_MONTH

        Returns the value formatted as a string, rounded to 2 decimal places.
        """

        estimate = int(num_instances) * instance_class_price * HOURS_PER_MONTH
        return "{estimate:.2f}".format(estimate=estimate)

    count = 0
    redis_cluster_data = json.load(open(json_file))

    print("Cache Cluster ID,Cache Cluster Type,Instance Class,Number of Nodes,Instance Class Price,Total Monthly Estimate")

    for redis_cluster in redis_cluster_data["CacheClusters"]:
        # If we set a processing limit and we haven't skipped, check to see if
        # we should stop.
        if limit > 0 and count >= limit:
            break

        output = "{cache_cluster_id},{cache_cluster_type},{instance_class},{num_nodes},{instance_class_price},{total_monthly_estimate}".format(
            cache_cluster_id=redis_cluster["CacheClusterId"],
            cache_cluster_type=redis_cluster["Engine"],
            instance_class=redis_cluster["CacheNodeType"],
            num_nodes=redis_cluster["NumCacheNodes"],
            instance_class_price=REDIS_PRICING_INFO[redis_cluster["CacheNodeType"]],
            total_monthly_estimate=calculate_monthly_cost(
                redis_cluster["NumCacheNodes"],
                REDIS_PRICING_INFO[redis_cluster["CacheNodeType"]]
            )
        )

        print(output)
        count += 1


def main():
    args = parse_args()

    limit = int(args.limit)

    if args.aws_service == "es":
        analyze_es(args.json_file, limit)
    elif args.aws_service == "rds":
        analyze_rds(args.json_file, limit)
    elif args.aws_service == "redis":
        analyze_redis(args.json_file, limit)
    elif args.aws_service == "aws-resource-tags":
        parse_aws_resource_tags(args.json_file, limit)
    else:
        print("Unknown command, exiting.")


if __name__ == "__main__":
    main()
