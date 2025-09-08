# cost-optimisation-aws

Getting fields from snapshots using .get() and [ ] access.

1. Using snapshot['SnapshotId']

This assumes the key must exist

If SnapshotId is missing, your code will raise a KeyError and crash.

In AWS describe_snapshots, the SnapshotId field is always present for every snapshot, so it’s safe and standard to use snapshot['SnapshotId'].

2. Using snapshot.get('SnapshotId').

This is safer because if the key is missing, it won’t crash — it will just return None (or a default value if you set one, e.g. .get('SnapshotId', 'unknown')).

It’s usually used for optional fields that may or may not be present. For example, VolumeId is sometimes missing (e.g. for snapshots copied from another region), which is why .get() is used there



| Field           | Always Present | Notes                                                                                                    |
| --------------- | -------------- | -------------------------------------------------------------------------------------------------------- |
| **SnapshotId**  | ✅ Yes          | Unique identifier for the snapshot. Always present.                                                      |
| **State**       | ✅ Yes          | `pending`, `completed`, or `error`.                                                                      |
| **StartTime**   | ✅ Yes          | When the snapshot started.                                                                               |
| **Progress**    | ✅ Yes          | % complete (string like `"100%"`).                                                                       |
| **OwnerId**     | ✅ Yes          | AWS account that owns the snapshot.                                                                      |
| **Description** | ❌ Optional     | Only present if snapshot has a description.                                                              |
| **VolumeId**    | ❌ Optional     | Present only if the snapshot was created from a volume. For copied/shared snapshots it might be missing. |
| **VolumeSize**  | ✅ Yes          | Size of volume in GiB.                                                                                   |
| **Tags**        | ❌ Optional     | Only present if you’ve added tags.                                                                       |
| **Encrypted**   | ✅ Yes          | Boolean, even if `False`.                                                                                |
| **KmsKeyId**    | ❌ Optional     | Only present if snapshot is encrypted with a CMK.                                                        |
| **OwnerAlias**  | ❌ Optional     | Shows `"amazon"` for public Amazon-owned snapshots.                                                      |
| **OutpostArn**  | ❌ Optional     | Only if created on an Outpost.                                                                           |
| **StorageTier** | ❌ Optional     | For archive snapshots (`standard` or `archive`).                                                         |
