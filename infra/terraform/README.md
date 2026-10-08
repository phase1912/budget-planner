# infra/terraform

Production on Google Cloud ([ADR-0014](../../docs/adr/0014-google-cloud-deployment.md)):
one root module, files split by concern, state in a GCS bucket. `terraform apply` is run
by hand from here; the Deploy workflow (`.github/workflows/deploy.yml`) only ships code
onto what this creates.

| File | Creates |
|---|---|
| `apis.tf` | The Google APIs everything else needs |
| `network.tf` | VPC, subnet, firewall (Postgres from the subnet only, SSH through IAP only) |
| `database.tf` | Postgres 16 on an e2-micro VM, its data disk, daily snapshots kept 7 days |
| `storage.tf` | The receipt photo bucket, reached keylessly as the backend's service account |
| `registry.tf` | Artifact Registry for backend images, keeping the last 5 |
| `secrets.tf` | Generated passwords and keys in Secret Manager |
| `run.tf` | The Cloud Run service and the migrations job |
| `appengine.tf` | The App Engine application the mail relay runs on (ADR-0013) |
| `firebase.tf` | Firebase and the Hosting site for the frontend |
| `github.tf` | Workload Identity Federation and the deployer service account |
| `budget.tf` | A monthly budget with alerts |

## First time

Needs `gcloud` and `terraform`, and an account that owns the project.

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project project-09a590a3-af55-42f3-998
```

**Bootstrap the state bucket.** This is done once, by hand, because Terraform cannot
store its state in a bucket it has not created yet:

```bash
gcloud storage buckets create gs://project-09a590a3-af55-42f3-998-tfstate \
  --location=us-central1 --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://project-09a590a3-af55-42f3-998-tfstate --versioning
```

The state holds every generated secret, so this bucket must stay private to the project.

**Apply:**

```bash
cp terraform.tfvars.example terraform.tfvars   # then fill in billing_account
terraform init -backend-config=bucket=project-09a590a3-af55-42f3-998-tfstate
terraform apply
```

Adding Firebase to the project can fail until its terms have been accepted once at
<https://console.firebase.google.com> (open the project there and continue). Then run
`terraform apply` again.

**Hand the outputs to GitHub.** Run the commands this prints, from the repository root:

```bash
terraform output -raw github_variables
```

Then run the Deploy workflow by hand once (Actions → Deploy → Run workflow), which ships
the backend, frontend and mail relay together for the first time.

## Day to day

- **Code changes** deploy themselves on merge to `main`.
- **Infrastructure changes:** edit the `.tf` files, open a PR (Terraform CI checks format
  and validity), and after merging run `terraform plan` and `terraform apply` here.
- **Look at the database:**

  ```bash
  gcloud compute ssh postgres --zone us-central1-a --tunnel-through-iap -- \
    docker exec -it postgres psql -U budget_planner budget_planner
  ```

## Restoring the database from a snapshot

Snapshots of the `pgdata` disk are taken daily at 03:00 UTC and kept for 7 days.

1. List the snapshots:

   ```bash
   gcloud compute snapshots list --filter="sourceDisk~pgdata"
   ```

2. Stop the VM:

   ```bash
   gcloud compute instances stop postgres --zone us-central1-a
   ```

3. Detach the current data disk and create a disk from the chosen snapshot under the same
   name:

   ```bash
   gcloud compute instances detach-disk postgres --disk pgdata --zone us-central1-a
   gcloud compute disks rename pgdata pgdata-broken --zone us-central1-a
   gcloud compute disks create pgdata --source-snapshot <snapshot> --type pd-standard --zone us-central1-a
   gcloud compute instances attach-disk postgres --disk pgdata --device-name pgdata --zone us-central1-a
   gcloud compute instances start postgres --zone us-central1-a
   ```

4. Check `/health`, then delete `pgdata-broken`. Terraform still recognises the restored
   disk, because its name is unchanged.

## Stopping costs

- **Pause:**

  ```bash
  gcloud compute instances stop postgres --zone us-central1-a
  ```

  The app then reports the database unreachable. Start the VM again before using it.
- **Remove everything:** `terraform destroy`. The `pgdata` disk is protected by
  `prevent_destroy`; remove that line first if the data really should go.
