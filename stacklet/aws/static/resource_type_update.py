"""Resource-type registry for update_tags-aws.py 

ResourceConfig here is the update-side dataclass (id_column + skip_columns),
defined in helpers.py -- not the list-side one.
"""

from helpers import ResourceConfig


RESOURCE_TYPES: dict[str, ResourceConfig] = {
    "acm-certificate":                        ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"domain_name", "status"}),
    ),
    "alarm":              ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state_value", "namespace"}),
    ),
    "ami":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"creation_date", "state", "architecture", "description"}),
    ),
    "app-elb":                ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"scheme", "vpc_id", "state", "type"}),
    ),
    "app-elb-target-group":                             ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"protocol", "port", "vpc_id", "target_type"}),
    ),
    "appstream-fleet":                        ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state", "instance_type"}),
    ),
    "appstream-stack":                        ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"description"}),
    ),
    "asg": ResourceConfig(id_column="arn", skip_columns=frozenset({"auto_scaling_group_name"})),
    "athena-work-group":                          ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state", "description"}),
    ),
    "cfn":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"stack_name", "stack_status", "creation_time", "description"}),
    ),
    "cloudhsm-backup": ResourceConfig(id_column="arn", skip_columns=frozenset({"backup_state", "cluster_id"})),
    "cloudhsm-cluster": ResourceConfig(id_column="arn", skip_columns=frozenset({"state"})),
    "comprehend-sentiment-detection-job":                                           ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"job_name", "job_status"}),
    ),
    "comprehend-topics-detection-job":                                        ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"job_name", "job_status"}),
    ),
    "customer-gateway":                         ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state", "type", "bgp_asn"}),
    ),
    "distribution":                     ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"domain_name", "status", "enabled"}),
    ),
    "dynamodb-table": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "ebs":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"}),
    ),
    "ebs-snapshot": ResourceConfig(id_column="arn", skip_columns=frozenset({"completion_time", "description"})),
    "ec2":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"instance_type", "state", "vpc_id"}),
    ),
    "ecr":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"repository_name", "repository_uri"}),
    ),
    "efs":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"life_cycle_state", "creation_time"}),
    ),
    "eks": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "elastic-ip":                   ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"public_ip", "domain", "instance_id"}),
    ),
    "elb": ResourceConfig(id_column="arn", skip_columns=frozenset({"dns_name", "scheme", "vpc_id"})),
    "event-bus":                  ResourceConfig(
        id_column="arn",
        skip_columns=frozenset(),
    ),
    "event-rule":                   ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state", "event_bus_name", "description"}),
    ),
    "firehose": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "flow-log":                 ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"resource_id", "flow_log_status"}),
    ),
    "globalaccelerator": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "status"})),
    "hostedzone":                   ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"zone_name", "record_count", "private"}),
    ),
    "iam-policy":                   ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"policy_name", "attachment_count", "create_date"}),
    ),
    "iam-role":                 ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"role_name", "create_date", "path", "description"}),
    ),
    "iam-user":                 ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"user_name", "create_date", "path"}),
    ),
    "internet-gateway":                         ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"attachment_state", "vpc_id"}),
    ),
    "key-pair":                 ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"key_name", "key_type", "key_fingerprint"}),
    ),
    "kms-key":                ResourceConfig(
        id_column="arn",
        skip_columns=frozenset(),
    ),
    "lambda":               ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"function_name", "runtime", "state", "description"}),
    ),
    "log-group":                  ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"retention_in_days", "creation_time"}),
    ),
    "nat-gateway":                    ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "subnet_id", "state"}),
    ),
    "network-acl":                    ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "is_default"}),
    ),
    "peering-connection":                           ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"status", "requester_vpc", "accepter_vpc"}),
    ),
    "prefix-list":                    ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"prefix_list_name", "state", "max_entries", "address_family"}),
    ),
    "rds":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"engine", "status", "instance_class"}),
    ),
    "rds-cluster":                    ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"engine", "status", "database_name"}),
    ),
    "rds-cluster-param-group":                                ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"family", "description"}),
    ),
    "rds-cluster-snapshot":                             ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"status", "snapshot_type", "engine"}),
    ),
    "rds-param-group":                        ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"family", "description"}),
    ),
    "rds-snapshot":                     ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"status", "snapshot_type", "allocated_storage"}),
    ),
    "rds-subnet-group":                         ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "subnet_group_status", "description"}),
    ),
    "rds-subscription":                         ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"status", "sns_topic_arn", "source_type"}),
    ),
    "resource-share-self": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "status"})),
    "route-table":                    ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id"}),
    ),
    "s3":           ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"creation_date"}),
    ),
    "s3-storage-lens": ResourceConfig(id_column="arn", skip_columns=frozenset({"id", "is_enabled"})),
    "secrets-manager":                        ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"description"}),
    ),
    "security-group":                       ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"group_name", "vpc_id", "description"}),
    ),
    "ses-email-identity": ResourceConfig(id_column="arn", skip_columns=frozenset({"identity_type", "verified_for_sending_status"})),
    "snapshot":                 ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"completion_time", "description"}),
    ),
    "sns":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset(),
    ),
    "sqs": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "ssm-document":                     ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"document_type", "document_version"}),
    ),
    "ssm-parameter":                      ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"type", "data_type", "description"}),
    ),
    "subnet":               ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_id", "cidr_block", "state", "available_ips"}),
    ),
    "transit-attachment":                           ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"transit_gateway_id", "resource_type", "state"}),
    ),
    "vpc":            ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"cidr_block", "state", "is_default"}),
    ),
    "vpc-endpoint":                     ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"vpc_endpoint_type", "vpc_id", "state"}),
    ),
    "vpn-connection":                       ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state", "type", "customer_gateway_id"}),
    ),
    "vpn-gateway":                    ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"state", "type"}),
    ),
    "waf-regional": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
    "wafv2": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "id"})),
    "xray-group":                   ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"group_name"}),
    ),
    "xray-rule":                  ResourceConfig(
        id_column="arn",
        skip_columns=frozenset({"rule_name", "priority", "fixed_rate"}),
    ),
    "directory": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "edition", "description"})),
    "dlm-policy": ResourceConfig(id_column="arn", skip_columns=frozenset({"state", "policy_type", "description"})),
    "ecs": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "ecs-task-definition": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "ses-configuration-set": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
    "ses-configuration-set-v2": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
    "workspaces-image": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "state", "os", "description"})),
    "workspaces": ResourceConfig(id_column="arn", skip_columns=frozenset({"state", "directory_id", "bundle_id"})),
    "redshift-snapshot": ResourceConfig(id_column="arn", skip_columns=frozenset({"cluster_identifier", "status"})),
    "workspaces-directory": ResourceConfig(id_column="arn", skip_columns=frozenset({"directory_name", "alias", "directory_type"})),
}
