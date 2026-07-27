"""Single source of truth for GCP resource types .

    meta_columns  the non-label columns after self_link
    list_fn       project -> [ {name, region, self_link, meta:[...], labels:{}} ].
    backend_fn    (self_link, project)->(read_current, apply_labels) for the update step. 
                  read_current()->(labels: dict, fingerprint|None);
                  apply_labels(merged:dict,fingerprint) writes the merged set.

Cloud client libraries are imported lazily inside each function so that, e.g.,
listing instances doesn't import the BigQuery client.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class GcpResourceConfig:
    meta_columns: tuple[str, ...]                 # columns between self_link and rbrk_*
    list_fn: Callable[[str], list[dict]]          # project -> row dicts
    backend_fn: Callable[[str, str], tuple]       # (self_link, project) -> (read_current, apply_labels)
    id_column: str = "self_link"

    @property
    def skip_columns(self) -> frozenset:
        """Derived so the update side never re-declares metadata columns."""
        return frozenset(self.meta_columns)


def _short(url: str) -> str:
    """Last path segment of a GCP resource URL ('.../machineTypes/e2-small' -> 'e2-small')."""
    return url.rsplit("/", 1)[-1] if url else ""


# ---------------------------------------------------------------------------
# Compute Engine (instances, disks, images)
# ---------------------------------------------------------------------------

def _list_instances(project: str) -> list[dict]:
    from google.cloud import compute_v1
    client = compute_v1.InstancesClient()
    out = []
    for _scope, scoped in client.aggregated_list(project=project):
        for inst in getattr(scoped, "instances", []) or []:
            zone = _short(inst.zone)
            out.append({
                "name": inst.name,
                "region": zone,
                "self_link": inst.self_link,
                "meta": [_short(inst.machine_type), inst.status, zone],
                "labels": dict(inst.labels or {}),
            })
    return out


def _list_disks(project: str) -> list[dict]:
    from google.cloud import compute_v1
    out = []
    zonal = compute_v1.DisksClient()
    for _scope, scoped in zonal.aggregated_list(project=project):
        for d in getattr(scoped, "disks", []) or []:
            out.append({
                "name": d.name,
                "region": _short(d.zone),
                "self_link": d.self_link,
                "meta": [str(d.size_gb or ""), d.status, _short(d.type_)],
                "labels": dict(d.labels or {}),
            })
    # Regional disks have no aggregatedList -> iterate regions.
    import sys
    regions_client = compute_v1.RegionsClient()
    region_disks = compute_v1.RegionDisksClient()
    for region in regions_client.list(project=project):
        try:
            for d in region_disks.list(project=project, region=region.name):
                out.append({
                    "name": d.name,
                    "region": _short(d.region),
                    "self_link": d.self_link,
                    "meta": [str(d.size_gb or ""), d.status, _short(d.type_)],
                    "labels": dict(d.labels or {}),
                })
        except Exception as e:
            print(f"  Warning: regional disks in {region.name} skipped ({e})", file=sys.stderr)
    return out


def _list_images(project: str) -> list[dict]:
    from google.cloud import compute_v1
    client = compute_v1.ImagesClient()
    return [{
        "name": img.name,
        "region": "global",
        "self_link": img.self_link,
        "meta": [img.family, img.status, str(img.disk_size_gb or "")],
        "labels": dict(img.labels or {}),
    } for img in client.list(project=project)]


def _backend_instance(self_link: str, project: str):
    from google.cloud import compute_v1
    parts = self_link.split("/")
    p = _seg_after(parts, "projects", project)
    zone = _seg_after(parts, "zones")
    name = parts[-1]
    client = compute_v1.InstancesClient()

    def read_current():
        o = client.get(project=p, zone=zone, instance=name)
        return dict(o.labels or {}), o.label_fingerprint

    def apply_labels(merged, fp):
        client.set_labels(
            project=p, zone=zone, instance=name,
            instances_set_labels_request_resource=compute_v1.InstancesSetLabelsRequest(
                labels=merged, label_fingerprint=fp),
        ).result()

    return read_current, apply_labels


def _backend_disk(self_link: str, project: str):
    """Zonal or regional disk, decided by the self_link scope segment."""
    from google.cloud import compute_v1
    parts = self_link.split("/")
    p = _seg_after(parts, "projects", project)
    name = parts[-1]

    if "zones" in parts:
        zone = _seg_after(parts, "zones")
        client = compute_v1.DisksClient()

        def read_current():
            o = client.get(project=p, zone=zone, disk=name)
            return dict(o.labels or {}), o.label_fingerprint

        def apply_labels(merged, fp):
            client.set_labels(
                project=p, zone=zone, resource=name,
                zone_set_labels_request_resource=compute_v1.ZoneSetLabelsRequest(
                    labels=merged, label_fingerprint=fp),
            ).result()

        return read_current, apply_labels

    region = _seg_after(parts, "regions")
    client = compute_v1.RegionDisksClient()

    def read_current():
        o = client.get(project=p, region=region, disk=name)
        return dict(o.labels or {}), o.label_fingerprint

    def apply_labels(merged, fp):
        client.set_labels(
            project=p, region=region, resource=name,
            region_set_labels_request_resource=compute_v1.RegionSetLabelsRequest(
                labels=merged, label_fingerprint=fp),
        ).result()

    return read_current, apply_labels


def _backend_image(self_link: str, project: str):
    from google.cloud import compute_v1
    parts = self_link.split("/")
    p = _seg_after(parts, "projects", project)
    name = parts[-1]
    client = compute_v1.ImagesClient()

    def read_current():
        o = client.get(project=p, image=name)
        return dict(o.labels or {}), o.label_fingerprint

    def apply_labels(merged, fp):
        client.set_labels(
            project=p, resource=name,
            global_set_labels_request_resource=compute_v1.GlobalSetLabelsRequest(
                labels=merged, label_fingerprint=fp),
        ).result()

    return read_current, apply_labels


# ---------------------------------------------------------------------------
# Cloud Storage (buckets)
# ---------------------------------------------------------------------------

def _list_buckets(project: str) -> list[dict]:
    from google.cloud import storage
    client = storage.Client(project=project)
    return [{
        "name": b.name,
        "region": (b.location or "").lower(),   # "US"/"US-CENTRAL1" -> lowercased
        "self_link": f"gs://{b.name}",
        "meta": [b.storage_class or "", b.location_type or ""],
        "labels": dict(b.labels or {}),
    } for b in client.list_buckets()]


def _backend_bucket(self_link: str, project: str):
    from google.cloud import storage
    name = self_link[len("gs://"):] if self_link.startswith("gs://") else self_link
    client = storage.Client(project=project)

    def read_current():
        b = client.get_bucket(name)
        return dict(b.labels or {}), None

    def apply_labels(merged, _fp):
        b = client.get_bucket(name)
        b.labels = merged
        b.patch()

    return read_current, apply_labels


# ---------------------------------------------------------------------------
# BigQuery (datasets)
# ---------------------------------------------------------------------------

def _list_bq_datasets(project: str) -> list[dict]:
    from google.cloud import bigquery
    client = bigquery.Client(project=project)
    out = []
    for item in client.list_datasets(project=project):
        ds = client.get_dataset(item.reference)   # list items lack labels/location
        out.append({
            "name": ds.dataset_id,
            "region": (ds.location or "").lower(),
            "self_link": f"{project}:{ds.dataset_id}",
            "meta": [ds.friendly_name or ""],
            "labels": dict(ds.labels or {}),
        })
    return out


def _backend_bq(self_link: str, project: str):
    from google.cloud import bigquery
    proj, _, dsid = self_link.partition(":")
    proj = proj or project
    client = bigquery.Client(project=proj)
    ref = f"{proj}.{dsid}"

    def read_current():
        ds = client.get_dataset(ref)
        return dict(ds.labels or {}), None

    def apply_labels(merged, _fp):
        ds = client.get_dataset(ref)
        ds.labels = merged
        client.update_dataset(ds, ["labels"])

    return read_current, apply_labels


def _seg_after(parts: list[str], key: str, default: str | None = None) -> str:
    """Return the path segment following `key` in a split self_link."""
    try:
        return parts[parts.index(key) + 1]
    except (ValueError, IndexError):
        if default is not None:
            return default
        raise ValueError(f"no '{key}' segment in self_link parts: {'/'.join(parts)}")


RESOURCE_TYPES: dict[str, GcpResourceConfig] = {
    "instance": GcpResourceConfig(
        meta_columns=("machine_type", "status", "zone"),
        list_fn=_list_instances, backend_fn=_backend_instance,
    ),
    "disk": GcpResourceConfig(
        meta_columns=("size_gb", "status", "type"),
        list_fn=_list_disks, backend_fn=_backend_disk,
    ),
    "image": GcpResourceConfig(
        meta_columns=("family", "status", "disk_size_gb"),
        list_fn=_list_images, backend_fn=_backend_image,
    ),
    "bucket": GcpResourceConfig(
        meta_columns=("storage_class", "location_type"),
        list_fn=_list_buckets, backend_fn=_backend_bucket,
    ),
    "bq-dataset": GcpResourceConfig(
        meta_columns=("friendly_name",),
        list_fn=_list_bq_datasets, backend_fn=_backend_bq,
    ),
}
