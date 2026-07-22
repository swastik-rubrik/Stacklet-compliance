"""Resource-type registry for update_tags-aws.py 

ResourceConfig here is the update-side dataclass (id_column + skip_columns),
defined in update_tags_common.py -- not the list-side one.
"""

from update_tags_common import ResourceConfig

RESOURCE_TYPES: dict[str, ResourceConfig] = {
    "ec2": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"instance_type", "state", "vpc_id"}),
    ),
    "ami": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"creation_date", "state", "architecture", "description"}),
    ),
    "ebs": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"}),
    ),
    "snapshot": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"completion_time", "description"}),
    ),
    "vpc": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"cidr_block", "state", "is_default"}),
    ),
    "subnet": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "cidr_block", "state", "available_ips"}),
    ),
    "route-table": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id"}),
    ),
    "internet-gateway": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"attachment_state", "vpc_id"}),
    ),
    "nat-gateway": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "subnet_id", "state"}),
    ),
    "vpc-endpoint": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_endpoint_type", "vpc_id", "state"}),
    ),
    "security-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"group_name", "vpc_id", "description"}),
    ),
    "network-acl": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "is_default"}),
    ),
    "prefix-list": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"prefix_list_name", "state", "max_entries", "address_family"}),
    ),
    "flow-log": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"resource_id", "flow_log_status"}),
    ),
    "rds": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"engine", "status", "instance_class"}),
    ),
    "rds-cluster": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"engine", "status", "database_name"}),
    ),
    "rds-snapshot": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"status", "snapshot_type", "allocated_storage"}),
    ),
    "rds-cluster-snapshot": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"status", "snapshot_type", "engine"}),
    ),
    "rds-param-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"family", "description"}),
    ),
    "rds-cluster-param-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"family", "description"}),
    ),
    "rds-subnet-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "subnet_group_status", "description"}),
    ),
    "rds-subscription": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"status", "sns_topic_arn", "source_type"}),
    ),
    "app-elb": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"scheme", "vpc_id", "state", "type"}),
    ),
    "app-elb-target-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"protocol", "port", "vpc_id", "target_type"}),
    ),
    "log-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"retention_in_days", "creation_time"}),
    ),
    "alarm": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state_value", "namespace"}),
    ),
    "event-bus": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset(),
    ),
    "event-rule": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state", "event_bus_name", "description"}),
    ),
    "cfn": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"stack_name", "stack_status", "creation_time", "description"}),
    ),
    "lambda": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"function_name", "runtime", "state", "description"}),
    ),
    "sns": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset(),
    ),
    "kms-key": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset(),
    ),
    "secrets-manager": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"description"}),
    ),
    "ssm-parameter": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"type", "data_type", "description"}),
    ),
    "iam-role": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"role_name", "create_date", "path", "description"}),
    ),
    "iam-user": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"user_name", "create_date", "path"}),
    ),
    "iam-policy": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"policy_name", "attachment_count", "create_date"}),
    ),
    "distribution": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"domain_name", "status", "enabled"}),
    ),
    "hostedzone": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"zone_name", "record_count", "private"}),
    ),
    "s3": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"creation_date"}),
    ),
}
