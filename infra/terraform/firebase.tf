# The frontend is a static Vite build on Firebase Hosting (ADR-0014). Adding Firebase to
# the project may first need its terms accepted once in the Firebase console.
resource "google_firebase_project" "this" {
  provider   = google-beta
  project    = var.project_id
  depends_on = [google_project_service.this]
}

resource "google_firebase_hosting_site" "frontend" {
  provider   = google-beta
  project    = var.project_id
  site_id    = var.hosting_site_id
  depends_on = [google_firebase_project.this]
}
