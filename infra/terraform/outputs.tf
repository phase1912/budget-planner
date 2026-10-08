output "backend_url" {
  description = "Public URL of the API."
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Where the app is served."
  value       = "https://${google_firebase_hosting_site.frontend.site_id}.web.app"
}

output "inbound_email_domain" {
  description = "Domain of every forwarding address."
  value       = "${var.project_id}.appspotmail.com"
}

output "image_repository" {
  description = "Where the Deploy workflow pushes backend images."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}"
}

output "workload_identity_provider" {
  description = "GCP_WORKLOAD_IDENTITY_PROVIDER for GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  description = "GCP_DEPLOYER_SERVICE_ACCOUNT for GitHub Actions."
  value       = google_service_account.deployer.email
}

output "github_variables" {
  description = "Repository variables the Deploy workflow reads; set them with these commands."
  value = join("\n", [
    "gh variable set GCP_PROJECT_ID --body ${var.project_id}",
    "gh variable set GCP_REGION --body ${var.region}",
    "gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body ${google_iam_workload_identity_pool_provider.github.name}",
    "gh variable set GCP_DEPLOYER_SERVICE_ACCOUNT --body ${google_service_account.deployer.email}",
    "gh variable set FIREBASE_SITE_ID --body ${var.hosting_site_id}",
    "gh variable set BACKEND_URL --body ${google_cloud_run_v2_service.backend.uri}",
  ])
}
