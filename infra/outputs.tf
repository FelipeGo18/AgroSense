output "service_url" {
  description = "La dirección pública de Cloud Run."
  value       = google_cloud_run_v2_service.app.uri
}

output "image_repository" {
  description = "Dónde sube el workflow las imágenes."
  value       = local.image_repo
}

output "github_wif_provider" {
  description = "Variable GCP_WIF_PROVIDER del entorno `produccion` de GitHub."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deploy_service_account" {
  description = "Variable GCP_DEPLOY_SA del entorno `produccion` de GitHub."
  value       = google_service_account.deploy.email
}
