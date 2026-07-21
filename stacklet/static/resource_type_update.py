"""Resource-type registry for update_tags-aws.py 

ResourceConfig here is the update-side dataclass (id_column + skip_columns),
defined in update_tags_common.py -- not the list-side one.
"""

from update_tags_common import ResourceConfig

RESOURCE_TYPES: dict[str, ResourceConfig] = {
    "snapshot": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"completion_time", "description"}),
    ),
    "volume": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"create_time", "size_gb", "state", "description"}),
    ),
    "instance": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"launch_time", "state", "instance_type", "vpc_id", "subnet_id"}),
    ),
    "ami": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"creation_date", "state", "description", "architecture"}),
    ),
    "security-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"description", "vpc_id"}),
    ),
    "prefix-list": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"prefix_list_name", "state", "max_entries", "address_family"}),
    ),
    "ebs": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"}),
    ),
    "vpc": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"cidr_block", "state", "is_default"}),
    ),
    "subnet": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "cidr_block", "state", "available_ips"}),
    ),
    "security-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"group_name", "vpc_id", "description"}),
    ),
    "network-acl": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "is_default"}),
    ),
    "internet-gateway": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"attachment_state", "vpc_id"}),
    ),
    "nat-gateway": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "subnet_id", "state"}),
    ),
    "log-group": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"retention_in_days", "creation_time"}),
    ),
    "sns": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset(),
    ),
    "cfn": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"stack_name", "stack_status", "creation_time", "description"}),
    ),
    "lambda": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"function_name", "runtime", "state", "description"}),
    ),
    "iam-role": ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"create_date", "max_session_duration", "description"}),
    ),
}
