# Receipt photos (ADR-0014). Private; photos are shown through presigned URLs only. The
# backend reaches the bucket as its service account: the organisation forbids service
# account keys, HMAC keys included, so there is no key at all.
resource "google_storage_bucket" "receipts" {
  name                        = "${var.project_id}-receipts"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  depends_on                  = [google_project_service.this]
}

resource "google_storage_bucket_iam_member" "backend_objects" {
  bucket = google_storage_bucket.receipts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend.email}"
}

# Presigned URLs are signed by IAM with the service account's Google-held key, which
# needs the account to be allowed to sign as itself.
resource "google_service_account_iam_member" "backend_signs_urls" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.backend.email}"
}
