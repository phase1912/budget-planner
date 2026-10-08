# GitHub Actions deploys as a service account through Workload Identity Federation: no
# JSON key exists, and only workflows on this repository's main branch can impersonate it.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.this]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/main'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  account_id   = "github-deployer"
  display_name = "GitHub Actions deployer"
  depends_on   = [google_project_service.this]
}

resource "google_service_account_iam_member" "deployer_from_github" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# What a deploy does: push the image, update the service and job, publish the frontend,
# deploy the mail relay (App Engine builds with Cloud Build and stages in Storage).
resource "google_project_iam_member" "deployer" {
  for_each = toset([
    "roles/run.developer",
    "roles/firebasehosting.admin",
    "roles/appengine.deployer",
    "roles/appengine.serviceAdmin",
    "roles/cloudbuild.builds.editor",
    "roles/storage.objectAdmin",
    "roles/serviceusage.serviceUsageConsumer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_artifact_registry_repository_iam_member" "deployer_pushes" {
  repository = google_artifact_registry_repository.backend.name
  location   = var.region
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

# Deploying a revision that runs as another service account requires acting as it.
resource "google_service_account_iam_member" "deployer_acts_as" {
  for_each = {
    backend    = google_service_account.backend.name
    app_engine = "projects/${var.project_id}/serviceAccounts/${var.project_id}@appspot.gserviceaccount.com"
  }

  service_account_id = each.value
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
  depends_on         = [google_app_engine_application.mail_relay]
}

resource "google_secret_manager_secret_iam_member" "deployer_reads_relay_secret" {
  secret_id = google_secret_manager_secret.this["inbound-email-secret"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.deployer.email}"
}
