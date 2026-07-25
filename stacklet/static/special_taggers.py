import sys
from update_tags_common import TagChange, format_change_line

# -----------------------------------------------------------------------------
# Special taggers -- for resource types RGT can't handle from the CSV region:
# globals (CloudFront/Route 53/S3) and RGT-unsupported types (Auto Scaling).
# IAM is NOT here -- RGT covers IAM, so it uses the default RGT tagger.
# -----------------------------------------------------------------------------

def _plan_changes(resources, current_by_id, region):
    """Return (changes, to_apply). changes = TagChange rows with +/~/= actions;
    to_apply = [(key, tags)] for resources with at least one add/update."""
    changes: list[TagChange] = []
    to_apply = []
    for rid, tags in resources:
        existing = current_by_id.get(rid, {})
        needs = False
        for t in tags:
            k, new = t["Key"], t["Value"]
            if k not in existing:
                changes.append(TagChange(rid, region, k, "+", "", new)); needs = True
            elif existing[k] != new:
                changes.append(TagChange(rid, region, k, "~", existing[k], new)); needs = True
            else:
                changes.append(TagChange(rid, region, k, "=", existing[k], new))
        if needs:
            to_apply.append((rid, tags))
    return changes, to_apply


def _finish_native(dry_run, resources, changes, to_apply, apply_one, summarize, verbose, verbose_out):
    """Shared tail: dry-run counts all in scope; apply writes only changed and surfaces per-resource failures."""
    if dry_run:
        if verbose:
            for c in changes:
                line = format_change_line(c)
                if line:
                    print(line, file=verbose_out)
        return len(resources), 0, (changes if summarize else [])
    tagged = errored = 0
    for key, tags in to_apply:
        try:
            apply_one(key, tags)
            tagged += 1
            if verbose:
                print(f"  Tagged {key} ({len(tags)} tags)", file=verbose_out)
        except Exception as exc:
            print(f"  FAILED {key}: {exc}", file=sys.stderr)
            errored += 1
    return tagged, errored, []


def _tag_cloudfront(session, region, resources, dry_run, verbose, summarize, verbose_out=sys.stdout):
    cf = session.client("cloudfront", region_name="us-east-1")  # CloudFront is global -> us-east-1
    current = {}
    for arn, _ in resources:
        try:
            items = cf.list_tags_for_resource(Resource=arn)["Tags"].get("Items", [])
            current[arn] = {t["Key"]: t["Value"] for t in items}
        except Exception:
            current[arn] = {}
    changes, to_apply = _plan_changes(resources, current, region)

    def apply_one(arn, tags):
        cf.tag_resource(Resource=arn, Tags={"Items": [{"Key": t["Key"], "Value": t["Value"]} for t in tags]})

    return _finish_native(dry_run, resources, changes, to_apply, apply_one, summarize, verbose, verbose_out)


def _tag_route53(session, region, resources, dry_run, verbose, summarize, verbose_out=sys.stdout):
    r53 = session.client("route53")  # global endpoint
    current = {}
    for arn, _ in resources:
        zid = arn.split("/")[-1]  # arn:...:hostedzone/ID -> ID
        try:
            tags = r53.list_tags_for_resource(ResourceType="hostedzone", ResourceId=zid)["ResourceTagSet"]["Tags"]
            current[arn] = {t["Key"]: t["Value"] for t in tags}
        except Exception:
            current[arn] = {}
    changes, to_apply = _plan_changes(resources, current, region)

    def apply_one(arn, tags):
        zid = arn.split("/")[-1]
        r53.change_tags_for_resource(
            ResourceType="hostedzone", ResourceId=zid,
            AddTags=[{"Key": t["Key"], "Value": t["Value"]} for t in tags],
        )

    return _finish_native(dry_run, resources, changes, to_apply, apply_one, summarize, verbose, verbose_out)


def _tag_s3(session, region, resources, dry_run, verbose, summarize, verbose_out=sys.stdout):
    # S3 put_bucket_tagging REPLACES the whole tag set -> read + merge per bucket,
    # in the bucket's home region.
    def bucket_of(arn):
        return arn.split(":::")[-1]

    current, region_of = {}, {}
    loc_client = session.client("s3", region_name="us-east-1")
    for arn, _ in resources:
        b = bucket_of(arn)
        try:
            loc = loc_client.get_bucket_location(Bucket=b).get("LocationConstraint") or "us-east-1"
            region_of[arn] = loc
            s3 = session.client("s3", region_name=loc)
            try:
                current[arn] = {t["Key"]: t["Value"] for t in s3.get_bucket_tagging(Bucket=b)["TagSet"]}
            except Exception:
                current[arn] = {}  # NoSuchTagSet -> no tags yet
        except Exception:
            current[arn] = {}
            region_of[arn] = "us-east-1"
    changes, to_apply = _plan_changes(resources, current, region)

    def apply_one(arn, tags):
        b = bucket_of(arn)
        s3 = session.client("s3", region_name=region_of.get(arn, "us-east-1"))
        merged = dict(current.get(arn, {}))          # preserve existing (incl. non-rbrk_) tags
        for t in tags:
            merged[t["Key"]] = t["Value"]
        s3.put_bucket_tagging(Bucket=b, Tagging={"TagSet": [{"Key": k, "Value": v} for k, v in merged.items()]})

    return _finish_native(dry_run, resources, changes, to_apply, apply_one, summarize, verbose, verbose_out)


def _tag_asg(session, region, resources, dry_run, verbose, summarize, verbose_out=sys.stdout):
    asg = session.client("autoscaling", region_name=region)

    def name_of(arn):
        return arn.split("autoScalingGroupName/")[-1]

    names = [name_of(a) for a, _ in resources]
    current = {n: {} for n in names}
    try:
        paginator = asg.get_paginator("describe_tags")
        for page in paginator.paginate(Filters=[{"Name": "auto-scaling-group", "Values": names}]):
            for t in page["Tags"]:
                current.setdefault(t["ResourceId"], {})[t["Key"]] = t["Value"]
    except Exception:
        pass
    res_by_name = [(name_of(a), tags) for a, tags in resources]
    changes, to_apply = _plan_changes(res_by_name, current, region)

    def apply_one(name, tags):
        asg.create_or_update_tags(Tags=[
            {"ResourceId": name, "ResourceType": "auto-scaling-group",
             "Key": t["Key"], "Value": t["Value"], "PropagateAtLaunch": False}
            for t in tags
        ])

    return _finish_native(dry_run, resources, changes, to_apply, apply_one, summarize, verbose, verbose_out)


def _tag_s3_storage_lens(session, region, resources, dry_run, verbose, summarize, verbose_out=sys.stdout):
    # Storage Lens configs are tagged via s3control (not RGT). ARN:
    # arn:aws:s3:<region>:<account>:storage-lens/<config-id>. put REPLACES tags -> merge.
    def parts(arn):
        p = arn.split(":")
        return p[3], p[4], arn.split("storage-lens/")[-1]  # region, account, config_id

    current = {}
    for arn, _ in resources:
        r, acct, cid = parts(arn)
        try:
            c = session.client("s3control", region_name=r)
            tags = c.get_storage_lens_configuration_tagging(ConfigId=cid, AccountId=acct).get("Tags", [])
            current[arn] = {t["Key"]: t["Value"] for t in tags}
        except Exception:
            current[arn] = {}
    changes, to_apply = _plan_changes(resources, current, region)

    def apply_one(arn, tags):
        r, acct, cid = parts(arn)
        c = session.client("s3control", region_name=r)
        merged = dict(current.get(arn, {}))          # preserve existing tags (put replaces all)
        for t in tags:
            merged[t["Key"]] = t["Value"]
        c.put_storage_lens_configuration_tagging(
            ConfigId=cid, AccountId=acct,
            Tags=[{"Key": k, "Value": v} for k, v in merged.items()],
        )

    return _finish_native(dry_run, resources, changes, to_apply, apply_one, summarize, verbose, verbose_out)

# resource_type -> special handler. Custom handlers for these resources
SPECIAL_TAGGERS = {
    "distribution": _tag_cloudfront,
    "hostedzone": _tag_route53,
    "s3": _tag_s3,
    "asg": _tag_asg,
    "s3-storage-lens": _tag_s3_storage_lens,
}
