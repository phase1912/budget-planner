# Every credential is generated here and stored in Secret Manager; none is ever typed or
# committed. Their values also sit in Terraform state, which is why the state bucket is
# private to the project (README.md).

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "random_password" "jwt" {
  length  = 64
  special = false
}

resource "random_password" "inbound_email" {
  length  = 40
  special = false
}

locals {
  database_url = "postgresql+asyncpg://${local.database_user}:${random_password.database.result}@${google_compute_address.database.address}:5432/${local.database_name}"

  secrets = {
    "db-password"          = random_password.database.result
    "database-url"         = local.database_url
    "jwt-secret-key"       = random_password.jwt.result
    "inbound-email-secret" = random_password.inbound_email.result
  }
}

resource "google_secret_manager_secret" "this" {
  for_each = toset(keys(local.secrets))

  secret_id = each.value
  replication {
    auto {}
  }
  depends_on = [google_project_service.this]
}

resource "google_secret_manager_secret_version" "this" {
  for_each = toset(keys(local.secrets))

  secret      = google_secret_manager_secret.this[each.value].id
  secret_data = local.secrets[each.value]
}

resource "google_secret_manager_secret_iam_member" "backend_reads" {
  for_each = toset(["database-url", "jwt-secret-key", "inbound-email-secret"])

  secret_id = google_secret_manager_secret.this[each.value].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}
