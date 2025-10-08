import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone, timedelta


ORG_ROLE_NAME = "SnapshotAuditRole"

def assume_role(account_id, role_name):
    sts = boto3.client("sts")
    response = sts.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="SnapshotAuditSession"
    )
    creds = response['Credentials']
    return boto3.client(
        "ec2",
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken'],
        region_name="us-east-1"
    )

def lambda_handler(event, context):
    org = boto3.client("organizations")
    accounts = org.list_accounts()["Accounts"]
    
    for account in accounts:
        account_id = account["Id"]  # ✅ corrected
        print(f"Checking account {account_id}...")

        # Collecting running instance IDs
        active_instance_ids = set()
        ec2 = assume_role(account_id, ORG_ROLE_NAME)
        ec2_paginator = ec2.get_paginator('describe_instances')
        for pages in ec2_paginator.paginate(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        ):
            for res in pages.get('Reservations', []):
                for inst in res.get('Instances', []):
                    active_instance_ids.add(inst['InstanceId'])

        # Only act on snapshots older than 7 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        try:
            snap_paginator = ec2.get_paginator("describe_snapshots")  # ✅ fixed

            for page in snap_paginator.paginate(OwnerIds=['self']):
                for snapshot in page.get('Snapshots', []):
                    snapshot_id = snapshot['SnapshotId']
                    volume_id = snapshot.get('VolumeId')   # ✅ fixed
                    start_time = snapshot.get('StartTime') 
                    state = snapshot.get('State')
                    volume_size = snapshot.get('VolumeSize')

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
                        continue   # ✅ now safe to continue

                    # Else: the volume exists
                    try:
                        vol = ec2.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
                    except ClientError as e:
                        code = e.response['Error'].get('Code')
                        if code == 'InvalidVolume.NotFound':
                            # If the source volume is gone
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

                    # If the volume exists, check attachments
                    attachments = vol.get('Attachments', [])
                    if not attachments:
                        # Volume exists but detached
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
                            print(f"Kept snapshot {snapshot_id}: volume attached but instance not running.")
                        else:
                            print(f"Kept snapshot {snapshot_id}: in active use.")
        except Exception as e:
            print(f"Error scanning account {account_id}: {e}")
