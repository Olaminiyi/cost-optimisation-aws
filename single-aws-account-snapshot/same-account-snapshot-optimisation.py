import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')

    # Collect running instance IDs
    active_instance_ids = set()
    paginator = ec2.get_paginator('describe_instances')
    for page in paginator.paginate(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    ):
        for res in page.get('Reservations', []):
            for inst in res.get('Instances', []):
                active_instance_ids.add(inst['InstanceId'])

    # only act on snapshots older than 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    snap_paginator = ec2.get_paginator('describe_snapshots')
    for page in snap_paginator.paginate(OwnerIds=['self']):
        for snapshot in page.get('Snapshots', []):
            snapshot_id = snapshot['SnapshotId']
            volume_id = snapshot.get('VolumeId')
            start_time = snapshot.get('StartTime')  
            if start_time and start_time > cutoff:
                continue

            if not volume_id:
                # No source volume recorded 
                try:
                    ec2.delete_snapshot(SnapshotId=snapshot_id, DryRun=True)
                except ClientError as e:
                    if e.response['Error'].get('Code') == 'DryRunOperation':
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        print(f"Deleted snapshot {snapshot_id} (no source volume).")
                    else:
                        print(f"Skip {snapshot_id}: {e}")
                continue

            # if the volume exists?
            try:
                vol = ec2.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
            except ClientError as e:
                code = e.response['Error'].get('Code')
                if code == 'InvalidVolume.NotFound':
                    # Source volume gone, delete
                    try:
                        ec2.delete_snapshot(SnapshotId=snapshot_id, DryRun=True)
                    except ClientError as e2:
                        if e2.response['Error'].get('Code') == 'DryRunOperation':
                            ec2.delete_snapshot(SnapshotId=snapshot_id)
                            print(f"Deleted snapshot {snapshot_id} (source volume deleted).")
                        else:
                            print(f"Skip {snapshot_id}: {e2}")
                else:
                    print(f"Skip {snapshot_id}: {e}")
                continue

            # If the volume has attachments, check if any attachment is to a running instance
            attachments = vol.get('Attachments', [])
            if not attachments:
                # Volume exists but detached, then delete
                
                try:
                    ec2.delete_snapshot(SnapshotId=snapshot_id, DryRun=True)
                except ClientError as e:
                    if e.response['Error'].get('Code') == 'DryRunOperation':
                        ec2.delete_snapshot(SnapshotId=snapshot_id)
                        print(f"Deleted snapshot {snapshot_id} (volume detached).")
                    else:
                        print(f"Skip {snapshot_id}: {e}")
            else:
                # Check if attached to any running instance
                attached_running = any(
                    att.get('InstanceId') in active_instance_ids
                    for att in attachments
                )
                if not attached_running:
                    # Attached, but not to a running instance 
                    #  we will we keep it.
                    print(f"Kept snapshot {snapshot_id}: volume attached but instance not running.")
                else:
                    # Keep snapshots for volumes attached to running instances
                    print(f"Kept snapshot {snapshot_id}: in active use.")
