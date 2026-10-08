# The inbound mail relay (ADR-0013) is the only thing on App Engine; its code is
# deployed by the Deploy workflow from infra/mail-relay-appengine.
resource "google_app_engine_application" "mail_relay" {
  project     = var.project_id
  location_id = var.app_engine_location
  depends_on  = [google_project_service.this]
}

# `gcloud app deploy` builds the relay with Cloud Build running as App Engine's default
# service account. New organisations no longer grant default service accounts any role
# automatically (iam.automaticIamGrantsForDefaultServiceAccounts), so it gets what a build
# needs: run the build, write its logs and image, and read the uploaded source from App
# Engine's staging bucket — that bucket only, not the receipt photos.
locals {
  app_engine_account = "serviceAccount:${var.project_id}@appspot.gserviceaccount.com"
}

resource "google_project_iam_member" "app_engine_builder" {
  for_each = toset([
    "roles/cloudbuild.builds.builder",
    "roles/logging.logWriter",
    "roles/artifactregistry.writer",
  ])

  project    = var.project_id
  role       = each.value
  member     = local.app_engine_account
  depends_on = [google_app_engine_application.mail_relay]
}

resource "google_storage_bucket_iam_member" "app_engine_reads_staging" {
  for_each = toset(["roles/storage.legacyBucketReader", "roles/storage.objectViewer"])

  bucket     = "staging.${var.project_id}.appspot.com"
  role       = each.value
  member     = local.app_engine_account
  depends_on = [google_app_engine_application.mail_relay]
}
