# One subnet holds both the database VM and the backend's Direct VPC egress addresses,
# so "from the subnet" is exactly "from the backend or the VM itself".
resource "google_compute_network" "main" {
  name                    = "budget-planner"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.this]
}

resource "google_compute_subnetwork" "main" {
  name                     = "budget-planner-${var.region}"
  network                  = google_compute_network.main.id
  region                   = var.region
  ip_cidr_range            = "10.10.0.0/24"
  private_ip_google_access = true
}

resource "google_compute_firewall" "postgres_from_subnet" {
  name          = "allow-postgres-from-subnet"
  network       = google_compute_network.main.id
  direction     = "INGRESS"
  source_ranges = [google_compute_subnetwork.main.ip_cidr_range]
  target_tags   = ["postgres"]

  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }
}

# SSH only through Identity-Aware Proxy (gcloud compute ssh --tunnel-through-iap), for
# restores and maintenance; nothing on the VM is reachable from the internet.
resource "google_compute_firewall" "ssh_from_iap" {
  name          = "allow-ssh-from-iap"
  network       = google_compute_network.main.id
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["postgres"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
