# Signing in with Google and Apple (F1.6, ADR-0035). Off until the client ids are set in
# terraform.tfvars; nothing here is applied without the owner's go-ahead.
#
# Apple's key (.p8) is never generated or committed: once apple_key_id is set, the secret
# below exists and its value is added by hand —
#   gcloud secrets versions add apple-sign-in-key --data-file=AuthKey_<KEY_ID>.p8
# — before the next deploy, or the revision cannot start.

locals {
  apple_key_on = var.apple_key_id != ""

  sign_in_env = merge(
    {
      GOOGLE_CLIENT_IDS = jsonencode(var.google_client_ids)
      APPLE_CLIENT_IDS  = jsonencode(var.apple_client_ids)
    },
    local.apple_key_on ? { APPLE_TEAM_ID = var.apple_team_id, APPLE_KEY_ID = var.apple_key_id } : {},
  )
  sign_in_secrets = local.apple_key_on ? { APPLE_PRIVATE_KEY = "apple-sign-in-key" } : {}
}

resource "google_secret_manager_secret" "apple_sign_in_key" {
  count = local.apple_key_on ? 1 : 0

  secret_id = "apple-sign-in-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.this]
}

resource "google_secret_manager_secret_iam_member" "backend_reads_apple_key" {
  count = local.apple_key_on ? 1 : 0

  secret_id = google_secret_manager_secret.apple_sign_in_key[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}
