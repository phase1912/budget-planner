terraform {
  required_version = ">= 1.9"

  # State lives in a GCS bucket created once by hand (see README.md, "Bootstrap");
  # the bucket name is passed at init: terraform init -backend-config=bucket=<name>.
  backend "gcs" {
    prefix = "production"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.20, < 8"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 6.20, < 8"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone

  # Budgets and Firebase are billed to this project's quota when run with user
  # credentials (gcloud auth application-default login).
  billing_project       = var.project_id
  user_project_override = true
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  zone                  = var.zone
  billing_project       = var.project_id
  user_project_override = true
}

data "google_project" "this" {}
