resource "google_artifact_registry_repository" "backend" {
  repository_id = "backend"
  location      = var.region
  format        = "DOCKER"
  depends_on    = [google_project_service.this]

  # Each deploy pushes an image; only the last few are worth paying storage for.
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-last-5"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }
  cleanup_policies {
    id     = "delete-the-rest"
    action = "DELETE"
    condition {
      tag_state = "ANY"
    }
  }
}
