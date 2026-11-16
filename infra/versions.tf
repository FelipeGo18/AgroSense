terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
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
  # Los presupuestos (Billing Budgets API) se cobran en cuota a este proyecto con las credenciales de usuario.
  billing_project       = var.project_id
  user_project_override = true
}
