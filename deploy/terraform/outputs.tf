output "service_url" {
  description = "The public URL of the Cloud Run API service"
  value       = google_cloud_run_v2_service.uid_api.uri
}

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID for epistemic candidates"
  value       = google_bigquery_dataset.epistemic_dataset.dataset_id
}

output "storage_bucket_url" {
  description = "Google Cloud Storage bucket URL for public candidate downloads"
  value       = google_storage_bucket.artifacts_bucket.url
}
