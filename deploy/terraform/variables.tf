variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
  default     = "universal-inverse-design"
}

variable "region" {
  description = "Google Cloud region for Cloud Run deployment"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run microservice"
  type        = string
  default     = "uid-engine-api"
}

variable "container_image" {
  description = "Artifact Registry or Container Registry image URI"
  type        = string
  default     = "gcr.io/universal-inverse-design/uid-engine-api:v0.7.0"
}

variable "max_instances" {
  description = "Maximum concurrent container instances (Hard cost ceiling)"
  type        = number
  default     = 2
}
