terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ─── 1. Google Cloud Run Serverless Service ───────────────────────────────────
# Configured for Scale-to-Zero ($0.00 base cost when idle)

resource "google_cloud_run_v2_service" "uid_api" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      ports {
        container_port = 8080
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "PORT"
        value = "8080"
      }
    }
  }
}

# ─── 2. Public Access IAM Binding ─────────────────────────────────────────────
# Allows unauthenticated public frontend requests from GitHub Pages & clients

resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.uid_api.location
  service  = google_cloud_run_v2_service.uid_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── 3. BigQuery Epistemic Data Sink (Free Tier < 10GB) ───────────────────────

resource "google_bigquery_dataset" "epistemic_dataset" {
  dataset_id                  = "uid_epistemic_data"
  friendly_name               = "UID Engine Epistemic Discoveries"
  description                 = "Stores generated candidate specs, QC telemetry, and 7-state graph logs."
  location                    = var.region
  default_table_expiration_ms = null # Permanent archival
}

# ─── 4. Public Artifact Storage Bucket ────────────────────────────────────────

resource "google_storage_bucket" "artifacts_bucket" {
  name                        = "${var.project_id}-public-artifacts"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.artifacts_bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
