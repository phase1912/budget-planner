# The inbound mail relay (ADR-0013) is the only thing on App Engine; its code is
# deployed by the Deploy workflow from infra/mail-relay-appengine.
resource "google_app_engine_application" "mail_relay" {
  project     = var.project_id
  location_id = var.app_engine_location
  depends_on  = [google_project_service.this]
}

# `gcloud app deploy` builds the relay with Cloud Build, which runs as the Compute Engine
# default service account. New organisations no longer grant that account any role
# automatically (iam.automaticIamGrantsForDefaultServiceAccounts), so it gets exactly
# what a build needs.
resource "google_project_iam_member" "app_engine_builder" {
  for_each = toset([
    "roles/cloudbuild.builds.builder",
    "roles/logging.logWriter",
    "roles/storage.objectViewer",
    "roles/artifactregistry.writer",
  ])

  project    = var.project_id
  role       = each.value
  member     = "serviceAccount:${data.google_project.this.number}-compute@developer.gserviceaccount.com"
  depends_on = [google_project_service.this]
}
