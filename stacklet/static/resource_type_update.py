"""Resource-type registry for update_tags-aws.py 

ResourceConfig here is the update-side dataclass (id_column + skip_columns),
defined in update_tags_common.py -- not the list-side one.
"""

from update_tags_common import ResourceConfig


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
    # ---- Added from stacklet-resource.json (skip_columns = list-side meta + trailing) ----
    "directory": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "edition", "description"})),
    "dlm-policy": ResourceConfig(id_column="arn", skip_columns=frozenset({"state", "policy_type", "description"})),
    "ecs": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "ecs-task-definition": ResourceConfig(id_column="arn", skip_columns=frozenset()),
    "ses-configuration-set": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
    "ses-configuration-set-v2": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
    "workspaces-image": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "state", "os", "description"})),
}

# #infosec-appsec-prod
# RESOURCE_TYPES: dict[str, ResourceConfig] = {
#     # ---- EC2 compute / storage --------------------------------------------
#     "ami": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"creation_date", "state", "architecture", "description"}),
#     ),
#     "ebs": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"}),
#     ),
#     "ebs-snapshot": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"completion_time", "description"}),
#     ),
#     "key-pair": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"key_name", "key_type", "key_fingerprint"}),
#     ),
#     "elastic-ip": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"public_ip", "domain", "instance_id"}),
#     ),
#     # ---- EC2 networking ---------------------------------------------------
#     "vpc": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "cidr_block", "is_default"}),
#     ),
#     "subnet": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "cidr_block", "availability_zone", "state"}),
#     ),
#     "security-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"group_name", "vpc_id", "description"}),
#     ),
#     "network-acl": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "is_default"}),
#     ),
#     "internet-gateway": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"attached_vpc"}),
#     ),
#     "nat-gateway": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "subnet_id", "state"}),
#     ),
#     "route-table": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id"}),
#     ),
#     "prefix-list": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"prefix_list_name", "state", "address_family"}),
#     ),
#     "flow-log": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"flow_log_status", "resource_id", "log_destination_type"}),
#     ),
#     "transit-attachment": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"transit_gateway_id", "resource_type", "state"}),
#     ),
#     # ---- RDS --------------------------------------------------------------
#     "rds-snapshot": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"snapshot_type", "status", "engine"}),
#     ),
#     "rds-param-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"db_parameter_group_family"}),
#     ),
#     "rds-subnet-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "status"}),
#     ),
#     # ---- CloudFormation ---------------------------------------------------
#     "cfn": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"stack_name", "stack_status", "creation_time"}),
#     ),
#     # ---- CloudWatch Logs --------------------------------------------------
#     "log-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"log_group_name", "retention_in_days", "creation_time"}),
#     ),
#     # ---- EventBridge ------------------------------------------------------
#     "event-bus": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"name"}),
#     ),
#     "event-rule": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"name", "state", "description"}),
#     ),
#     # ---- Athena -----------------------------------------------------------
#     "athena-work-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "description"}),
#     ),
#     # ---- X-Ray ------------------------------------------------------------
#     "xray-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"group_name"}),
#     ),
#     "xray-rule": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"rule_name", "priority", "fixed_rate"}),
#     ),
#     # ---- ELB --------------------------------------------------------------
#     "app-elb": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"dns_name", "type", "state"}),
#     ),
#     "app-elb-target-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"target_group_name", "protocol", "port"}),
#     ),
#     "elb": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"dns_name", "scheme", "vpc_id"}),
#     ),
#     # ---- Lambda -----------------------------------------------------------
#     "lambda": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"function_name", "runtime", "state", "description"}),
#     ),
#     # ---- ECR --------------------------------------------------------------
#     "ecr": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"repository_name", "repository_uri"}),
#     ),
#     # ---- KMS --------------------------------------------------------------
#     "kms-key": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset(),
#     ),
#     # ---- SSM --------------------------------------------------------------
#     "ssm-parameter": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"type", "data_type", "description"}),
#     ),
#     "ssm-document": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"document_type", "document_version"}),
#     ),
#     # ---- Comprehend -------------------------------------------------------
#     "comprehend-sentiment-detection-job": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"job_name", "job_status"}),
#     ),
#     "comprehend-topics-detection-job": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"job_name", "job_status"}),
#     ),
#     # ---- S3 Storage Lens --------------------------------------------------
#     "s3-storage-lens": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"id", "is_enabled"}),
#     ),
#     "s3": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"creation_date"}),
#     ),
# }

# # AWS Production logs
# RESOURCE_TYPES: dict[str, ResourceConfig] = {
#     "prefix-list": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"prefix_list_name", "state", "address_family"}),
#     ),
#     "event-rule": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"name", "state", "description"}),
#     ),
#     "subnet": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "cidr_block", "availability_zone", "state"}),
#     ),
#     "flow-log": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"flow_log_status", "resource_id", "log_destination_type"}),
#     ),
#     "athena-work-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "description"}),
#     ),
#     "event-bus": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"name"}),
#     ),
#     "internet-gateway": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"attached_vpc"}),
#     ),
#     "log-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"log_group_name", "retention_in_days", "creation_time"}),
#     ),
#     "network-acl": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "is_default"}),
#     ),
#     "route-table": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id"}),
#     ),
#     "vpc": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "cidr_block", "is_default"}),
#     ),
#     "xray-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"group_name"}),
#     ),
#     "xray-rule": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"rule_name", "priority", "fixed_rate"}),
#     ),
#     "ami": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"creation_date", "state", "architecture", "description"}),
#     ),
#     "s3": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"creation_date"}),
#     ),
#     "kms-key": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset(),
#     ),
#     "cfn": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"stack_name", "stack_status", "creation_time"}),
#     ),
#     "key-pair": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"key_name", "key_type", "key_fingerprint"}),
#     ),
#     "lambda": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"function_name", "runtime", "state", "description"}),
#     ),
#     "s3-storage-lens": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"id", "is_enabled"}),
#     ),
# }

# # AWS PRODUCTION SECURITY
# RESOURCE_TYPES: dict[str, ResourceConfig] = {
#     "ebs": ResourceConfig(id_column="arn", skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"})),
#     "security-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"group_name", "vpc_id", "description"})),
#     "ebs-snapshot": ResourceConfig(id_column="arn", skip_columns=frozenset({"completion_time", "description"})),
#     "ami": ResourceConfig(id_column="arn", skip_columns=frozenset({"creation_date", "state", "architecture", "description"})),
#     "acm-certificate": ResourceConfig(id_column="arn", skip_columns=frozenset({"domain_name", "status"})),
#     "log-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"log_group_name", "retention_in_days", "creation_time"})),
#     "subnet": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id", "cidr_block", "availability_zone", "state"})),
#     "event-rule": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "state", "description"})),
#     "key-pair": ResourceConfig(id_column="arn", skip_columns=frozenset({"key_name", "key_type", "key_fingerprint"})),
#     "s3": ResourceConfig(id_column="arn", skip_columns=frozenset({"creation_date"})),
#     "route-table": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id"})),
#     "cloudhsm-backup": ResourceConfig(id_column="arn", skip_columns=frozenset({"backup_state", "cluster_id"})),
#     "flow-log": ResourceConfig(id_column="arn", skip_columns=frozenset({"flow_log_status", "resource_id", "log_destination_type"})),
#     "lambda": ResourceConfig(id_column="arn", skip_columns=frozenset({"function_name", "runtime", "state", "description"})),
#     "cfn": ResourceConfig(id_column="arn", skip_columns=frozenset({"stack_name", "stack_status", "creation_time"})),
#     "network-acl": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id", "is_default"})),
#     "internet-gateway": ResourceConfig(id_column="arn", skip_columns=frozenset({"attached_vpc"})),
#     "ssm-parameter": ResourceConfig(id_column="arn", skip_columns=frozenset({"type", "data_type", "description"})),
#     "vpc": ResourceConfig(id_column="arn", skip_columns=frozenset({"state", "cidr_block", "is_default"})),
#     "kms-key": ResourceConfig(id_column="arn", skip_columns=frozenset()),
#     "rds-cluster-snapshot": ResourceConfig(id_column="arn", skip_columns=frozenset({"snapshot_type", "status", "engine"})),
#     "secrets-manager": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "last_changed_date", "description"})),
#     "vpc-endpoint": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id", "service_name", "state"})),
#     "athena-work-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"state", "description"})),
#     "event-bus": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
#     "xray-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"group_name"})),
#     "xray-rule": ResourceConfig(id_column="arn", skip_columns=frozenset({"rule_name", "priority", "fixed_rate"})),
#     "sns": ResourceConfig(id_column="arn", skip_columns=frozenset()),
#     "ec2": ResourceConfig(id_column="arn", skip_columns=frozenset({"instance_type", "state", "vpc_id"})),
#     "alarm": ResourceConfig(id_column="arn", skip_columns=frozenset({"alarm_name", "state_value", "metric_name"})),
#     "elastic-ip": ResourceConfig(id_column="arn", skip_columns=frozenset({"public_ip", "domain", "instance_id"})),
#     "rds-param-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"db_parameter_group_family"})),
#     "nat-gateway": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id", "subnet_id", "state"})),
#     "app-elb-target-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"target_group_name", "protocol", "port"})),
#     "rds-cluster-param-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"db_parameter_group_family"})),
#     "rds-subnet-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id", "status"})),
#     "sqs": ResourceConfig(id_column="arn", skip_columns=frozenset()),
#     "dynamodb-table": ResourceConfig(id_column="arn", skip_columns=frozenset()),
#     "ssm-document": ResourceConfig(id_column="arn", skip_columns=frozenset({"document_type", "document_version"})),
#     "transit-attachment": ResourceConfig(id_column="arn", skip_columns=frozenset({"transit_gateway_id", "resource_type", "state"})),
#     "asg": ResourceConfig(id_column="arn", skip_columns=frozenset({"auto_scaling_group_name"})),
#     "cloudhsm-cluster": ResourceConfig(id_column="arn", skip_columns=frozenset({"state"})),
#     "resource-share-self": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "status"})),
#     "waf-regional": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
#     "app-elb": ResourceConfig(id_column="arn", skip_columns=frozenset({"dns_name", "type", "state"})),
#     "ecr": ResourceConfig(id_column="arn", skip_columns=frozenset({"repository_name", "repository_uri"})),
#     "eks": ResourceConfig(id_column="arn", skip_columns=frozenset()),
#     "elb": ResourceConfig(id_column="arn", skip_columns=frozenset({"dns_name", "scheme", "vpc_id"})),
#     "firehose": ResourceConfig(id_column="arn", skip_columns=frozenset()),
#     "globalaccelerator": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "status"})),
#     "hostedzone": ResourceConfig(id_column="arn", skip_columns=frozenset({"zone_name", "record_count", "private"})),
#     "s3-storage-lens": ResourceConfig(id_column="arn", skip_columns=frozenset({"id", "is_enabled"})),
#     "ses-email-identity": ResourceConfig(id_column="arn", skip_columns=frozenset({"identity_type", "verified_for_sending_status"})),
#     "wafv2": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "id"})),
# }


# # aws-rubrikdev-infosec-secarch-dev
# RESOURCE_TYPES: dict[str, ResourceConfig] = {
#     "prefix-list": ResourceConfig(id_column="arn", skip_columns=frozenset({"prefix_list_name", "state", "address_family"})),
#     "subnet": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id", "cidr_block", "availability_zone", "state"})),
#     "event-rule": ResourceConfig(id_column="arn", skip_columns=frozenset({"name", "state", "description"})),
#     "iam-role": ResourceConfig(id_column="arn", skip_columns=frozenset({"role_name", "create_date", "path", "description"})),
#     "athena-work-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"state", "description"})),
#     "event-bus": ResourceConfig(id_column="arn", skip_columns=frozenset({"name"})),
#     "flow-log": ResourceConfig(id_column="arn", skip_columns=frozenset({"flow_log_status", "resource_id", "log_destination_type"})),
#     "internet-gateway": ResourceConfig(id_column="arn", skip_columns=frozenset({"attached_vpc"})),
#     "network-acl": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id", "is_default"})),
#     "route-table": ResourceConfig(id_column="arn", skip_columns=frozenset({"vpc_id"})),
#     "vpc": ResourceConfig(id_column="arn", skip_columns=frozenset({"state", "cidr_block", "is_default"})),
#     "xray-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"group_name"})),
#     "xray-rule": ResourceConfig(id_column="arn", skip_columns=frozenset({"rule_name", "priority", "fixed_rate"})),
#     "iam-policy": ResourceConfig(id_column="arn", skip_columns=frozenset({"policy_name", "attachment_count", "create_date"})),
#     "s3": ResourceConfig(id_column="arn", skip_columns=frozenset({"creation_date"})),
#     "iam-user": ResourceConfig(id_column="arn", skip_columns=frozenset({"user_name", "create_date", "path"})),
#     "ebs": ResourceConfig(id_column="arn", skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"})),
#     "lambda": ResourceConfig(id_column="arn", skip_columns=frozenset({"function_name", "runtime", "state", "description"})),
#     "s3-storage-lens": ResourceConfig(id_column="arn", skip_columns=frozenset({"id", "is_enabled"})),
#     "security-group": ResourceConfig(id_column="arn", skip_columns=frozenset({"group_name", "vpc_id", "description"})),
# }


# aws-rubrikinc-eks_golden_image-prod


# aws-rubrikinc-ror-prod


# FedRAMP-InfoSec-Dev

# infosec-deploy-testing



# infosec-dr-prod

# # lab
# RESOURCE_TYPES: dict[str, ResourceConfig] = {
#     "ebs": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"}),
#     ),
#     "prefix-list": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"prefix_list_name", "state", "address_family"}),
#     ),
#     "cfn": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"stack_name", "stack_status", "creation_time"}),
#     ),
#     "event-rule": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"name", "state", "description"}),
#     ),
#     "xray-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"group_name"}),
#     ),
#     "iam-role": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"role_name", "create_date", "path", "description"}),
#     ),
#     "iam-policy": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"policy_name", "attachment_count", "create_date"}),
#     ),
#     "athena-work-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "description"}),
#     ),
#     "xray-rule": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"rule_name", "priority", "fixed_rate"}),
#     ),
#     "efs": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"life_cycle_state", "creation_time"}),
#     ),
#     "ssm-document": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"document_type", "document_version"}),
#     ),
# }

# # playground
# RESOURCE_TYPES: dict[str, ResourceConfig] = {
#     "ec2": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"instance_type", "state", "vpc_id"}),
#     ),
#     "ami": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"creation_date", "state", "architecture", "description"}),
#     ),
#     "ebs": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"create_time", "size_gb", "state", "volume_type", "availability_zone"}),
#     ),
#     "snapshot": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"completion_time", "description"}),
#     ),
#     "vpc": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"cidr_block", "state", "is_default"}),
#     ),
#     "subnet": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "cidr_block", "state", "available_ips"}),
#     ),
#     "route-table": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id"}),
#     ),
#     "internet-gateway": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"attachment_state", "vpc_id"}),
#     ),
#     "nat-gateway": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "subnet_id", "state"}),
#     ),
#     "vpc-endpoint": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_endpoint_type", "vpc_id", "state"}),
#     ),
#     "security-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"group_name", "vpc_id", "description"}),
#     ),
#     "network-acl": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "is_default"}),
#     ),
#     "prefix-list": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"prefix_list_name", "state", "max_entries", "address_family"}),
#     ),
#     "flow-log": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"resource_id", "flow_log_status"}),
#     ),
#     "customer-gateway": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "type", "bgp_asn"}),
#     ),
#     "key-pair": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"key_name", "key_type", "key_fingerprint"}),
#     ),
#     "peering-connection": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"status", "requester_vpc", "accepter_vpc"}),
#     ),
#     "transit-attachment": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"transit_gateway_id", "resource_type", "state"}),
#     ),
#     "vpn-connection": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "type", "customer_gateway_id"}),
#     ),
#     "vpn-gateway": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "type"}),
#     ),
#     "elastic-ip": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"public_ip", "domain", "instance_id"}),
#     ),
#     "rds": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"engine", "status", "instance_class"}),
#     ),
#     "rds-cluster": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"engine", "status", "database_name"}),
#     ),
#     "rds-snapshot": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"status", "snapshot_type", "allocated_storage"}),
#     ),
#     "rds-cluster-snapshot": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"status", "snapshot_type", "engine"}),
#     ),
#     "rds-param-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"family", "description"}),
#     ),
#     "rds-cluster-param-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"family", "description"}),
#     ),
#     "rds-subnet-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"vpc_id", "subnet_group_status", "description"}),
#     ),
#     "rds-subscription": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"status", "sns_topic_arn", "source_type"}),
#     ),
#     "app-elb": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"scheme", "vpc_id", "state", "type"}),
#     ),
#     "app-elb-target-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"protocol", "port", "vpc_id", "target_type"}),
#     ),
#     "log-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"retention_in_days", "creation_time"}),
#     ),
#     "alarm": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state_value", "namespace"}),
#     ),
#     "event-bus": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset(),
#     ),
#     "event-rule": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "event_bus_name", "description"}),
#     ),
#     "cfn": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"stack_name", "stack_status", "creation_time", "description"}),
#     ),
#     "lambda": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"function_name", "runtime", "state", "description"}),
#     ),
#     "sns": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset(),
#     ),
#     "kms-key": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset(),
#     ),
#     "secrets-manager": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"description"}),
#     ),
#     "ssm-parameter": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"type", "data_type", "description"}),
#     ),
#     "iam-role": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"role_name", "create_date", "path", "description"}),
#     ),
#     "iam-user": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"user_name", "create_date", "path"}),
#     ),
#     "iam-policy": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"policy_name", "attachment_count", "create_date"}),
#     ),
#     "acm-certificate": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"domain_name", "status"}),
#     ),
#     "ecr": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"repository_name", "repository_uri"}),
#     ),
#     "xray-group": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"group_name"}),
#     ),
#     "appstream-fleet": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"state", "instance_type"}),
#     ),
#     "appstream-stack": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"description"}),
#     ),
#     "distribution": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"domain_name", "status", "enabled"}),
#     ),
#     "hostedzone": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"zone_name", "record_count", "private"}),
#     ),
#     "s3": ResourceConfig(
#         id_column="arn",
#         skip_columns=frozenset({"creation_date"}),
#     ),
# }


