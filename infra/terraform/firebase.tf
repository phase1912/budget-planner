# The frontend is a static Vite build on Firebase Hosting (ADR-0014). Adding Firebase to
# the project may first need its terms accepted once in the Firebase console.
resource "google_firebase_project" "this" {
  provider   = google-beta
  project    = var.project_id
  depends_on = [google_project_service.this]
}

# A site's name cannot change, so the shorter address is a second site (F17.1). The first
# one stays in state under a new name rather than being replaced: replacing it would delete
# it, and its address is the one people and search engines already know.
moved {
  from = google_firebase_hosting_site.frontend
  to   = google_firebase_hosting_site.legacy
}

resource "google_firebase_hosting_site" "app" {
  provider   = google-beta
  project    = var.project_id
  site_id    = var.hosting_site_id
  depends_on = [google_firebase_project.this]
}

resource "google_firebase_hosting_site" "legacy" {
  provider   = google-beta
  project    = var.project_id
  site_id    = var.legacy_hosting_site_id
  depends_on = [google_firebase_project.this]
}

# The old address serves nothing but a permanent redirect to the same path on the new one.
# It is released only once the new site exists — were the name taken, the apply fails before
# the old address stops serving the app — and only with `redirect_legacy`, which the first
# apply turns off so nobody is sent to the new site before the app is deployed to it
# (README.md, "Moving the address").
resource "google_firebase_hosting_version" "legacy_redirect" {
  count    = var.redirect_legacy ? 1 : 0
  provider = google-beta
  site_id  = google_firebase_hosting_site.legacy.site_id
  config {
    redirects {
      glob        = "/:path*"
      status_code = 301
      location    = "https://${google_firebase_hosting_site.app.site_id}.web.app/:path"
    }
  }
}

resource "google_firebase_hosting_release" "legacy_redirect" {
  count        = var.redirect_legacy ? 1 : 0
  provider     = google-beta
  site_id      = google_firebase_hosting_site.legacy.site_id
  version_name = google_firebase_hosting_version.legacy_redirect[0].name
  message      = "Moved to https://${google_firebase_hosting_site.app.site_id}.web.app (F17.1)"
}
