We will extend the Lambda to scan all developer accounts in the AWS Organization

We’ll use:

- Organizations API → to list all accounts.

- STS assume_role → to jump into each account (needs IAM role set up in each account).

- EC2 client → to fetch snapshots from each account.

## Step 1: Setup Cross-Account IAM Role

In each developer’s AWS account, create a role called SnapshotAuditRole with:

Trust policy allowing your central account (where Lambda runs) to assume it.

Permissions policy like:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSnapshots"
      ],
      "Resource": "*"
    }
  ]
}

```

