locals {
  frontend_origins = [
    "https://${var.hosting_site_id}.web.app",
    "https://${var.hosting_site_id}.firebaseapp.com",
  ]

  # Settings every backend process gets, service and migrations job alike.
  backend_env = {
    ENVIRONMENT          = "production"
    STORAGE_BACKEND      = "gcs"
    S3_BUCKET_NAME       = google_storage_bucket.receipts.name
    LLM_MODEL            = var.llm_model
    VERTEX_PROJECT       = var.project_id
    VERTEX_LOCATION      = var.region
    INBOUND_EMAIL_DOMAIN = "${var.project_id}.appspotmail.com"
    CORS_ORIGINS         = jsonencode(local.frontend_origins)
  }

  backend_secrets = {
    DATABASE_URL         = "database-url"
    JWT_SECRET_KEY       = "jwt-secret-key"
    INBOUND_EMAIL_SECRET = "inbound-email-secret"
  }
}

resource "google_service_account" "backend" {
  account_id   = "backend"
  display_name = "Backend (Cloud Run)"
  depends_on   = [google_project_service.this]
}

resource "google_project_iam_member" "backend_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_cloud_run_v2_service" "backend" {
  name                 = "backend"
  location             = var.region
  ingress              = "INGRESS_TRAFFIC_ALL"
  deletion_protection  = false
  invoker_iam_disabled = true # public API without an allUsers binding the org policy may forbid

  template {
    service_account                  = google_service_account.backend.email
    max_instance_request_concurrency = 40
    timeout                          = "300s"

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    vpc_access {
      egress = "PRIVATE_RANGES_ONLY"
      network_interfaces {
        network    = google_compute_network.main.id
        subnetwork = google_compute_subnetwork.main.id
      }
    }

    containers {
      image = var.backend_image

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        # Receipts are read in background tasks after the response is sent; CPU must
        # stay allocated for them (ADR-0014).
        cpu_idle          = false
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = local.backend_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.backend_secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.this[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 2
        period_seconds        = 5
        failure_threshold     = 12
      }
    }
  }

  lifecycle {
    # The Deploy workflow sets the image; Terraform must not roll it back.
    ignore_changes = [template[0].containers[0].image, client, client_version]
  }

  depends_on = [
    google_project_service.this,
    google_secret_manager_secret_iam_member.backend_reads,
    google_secret_manager_secret_version.this,
  ]
}

resource "google_cloud_run_v2_job" "migrate" {
  name                = "migrate"
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1
    template {
      service_account = google_service_account.backend.email
      max_retries     = 0
      timeout         = "600s"

      vpc_access {
        egress = "PRIVATE_RANGES_ONLY"
        network_interfaces {
          network    = google_compute_network.main.id
          subnetwork = google_compute_subnetwork.main.id
        }
      }

      containers {
        image   = var.backend_image
        command = ["alembic", "upgrade", "head"]

        dynamic "env" {
          for_each = local.backend_env
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = local.backend_secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.this[env.value].secret_id
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version]
  }

  depends_on = [google_secret_manager_secret_iam_member.backend_reads]
}
