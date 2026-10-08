# Postgres on the free-tier e2-micro (ADR-0014): 1 GB of RAM, a 10 GB boot disk and a
# 10 GB data disk, together inside the free 30 GB. Reachable only from the subnet.

locals {
  database_name = "budget_planner"
  database_user = "budget_planner"
}

resource "google_service_account" "database" {
  account_id   = "database-vm"
  display_name = "Postgres VM"
  depends_on   = [google_project_service.this]
}

resource "google_project_iam_member" "database_logs" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter"])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.database.email}"
}

resource "google_secret_manager_secret_iam_member" "database_reads_password" {
  secret_id = google_secret_manager_secret.this["db-password"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.database.email}"
}

resource "google_compute_address" "database" {
  name         = "postgres-internal"
  address_type = "INTERNAL"
  subnetwork   = google_compute_subnetwork.main.id
  region       = var.region
  address      = "10.10.0.10"
}

resource "google_compute_disk" "pgdata" {
  name = "pgdata"
  type = "pd-standard"
  size = 10
  zone = var.zone

  depends_on = [google_project_service.this]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_resource_policy" "daily_snapshots" {
  name       = "pgdata-daily"
  region     = var.region
  depends_on = [google_project_service.this]

  snapshot_schedule_policy {
    schedule {
      daily_schedule {
        days_in_cycle = 1
        start_time    = "03:00"
      }
    }
    retention_policy {
      max_retention_days    = 7
      on_source_disk_delete = "KEEP_AUTO_SNAPSHOTS"
    }
  }
}

resource "google_compute_disk_resource_policy_attachment" "pgdata" {
  name = google_compute_resource_policy.daily_snapshots.name
  disk = google_compute_disk.pgdata.name
  zone = var.zone
}

resource "google_compute_instance" "database" {
  name                      = "postgres"
  machine_type              = "e2-micro"
  zone                      = var.zone
  tags                      = ["postgres"]
  allow_stopping_for_update = true

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
      size  = 10
      type  = "pd-standard"
    }
  }

  attached_disk {
    source      = google_compute_disk.pgdata.id
    device_name = "pgdata"
  }

  network_interface {
    subnetwork = google_compute_subnetwork.main.id
    network_ip = google_compute_address.database.address

    # An ephemeral public address only so the VM can pull the Postgres image; the
    # firewall lets nothing in from the internet.
    access_config {}
  }

  metadata = {
    user-data = templatefile("${path.module}/templates/postgres-cloud-init.yaml", {
      project_id       = var.project_id
      password_secret  = "db-password"
      database_name    = local.database_name
      database_user    = local.database_user
      postgres_version = "16.4-alpine"
    })
    google-logging-enabled = "true"
  }

  service_account {
    email  = google_service_account.database.email
    scopes = ["cloud-platform"]
  }

  shielded_instance_config {
    enable_secure_boot = true
  }

  depends_on = [
    google_secret_manager_secret_version.this,
    google_secret_manager_secret_iam_member.database_reads_password,
  ]
}
