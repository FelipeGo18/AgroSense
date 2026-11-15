# Producción de AgroSense en Google Cloud (HU-023, HU-234, HU-235), en la capa gratuita:
# - Cloud Run (API + web), que escala a 0.
# - La base: PostgreSQL 17 en una VM e2-micro (gratis en us-east1), sin puerto público.
# - Artifact Registry para las imágenes; Secret Manager para la cadena de conexión.
# - Workload Identity Federation: GitHub Actions despliega desde `produccion` sin llaves JSON.

locals {
  services = [
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudbilling.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sts.googleapis.com",
  ]
  subnet_range = "10.10.0.0/24"
  image_repo   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}"
}

resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------------------------------------- imágenes

resource "google_artifact_registry_repository" "app" {
  location      = var.region
  repository_id = "agrosense"
  format        = "DOCKER"
  description   = "Imágenes de producción de AgroSense"

  # Solo las 3 imágenes más nuevas: la capa gratuita es de 0,5 GB.
  cleanup_policies {
    id     = "conservar-3"
    action = "KEEP"
    most_recent_versions {
      keep_count = 3
    }
  }
  cleanup_policies {
    id     = "borrar-viejas"
    action = "DELETE"
    condition {
      older_than = "86400s"
    }
  }

  depends_on = [google_project_service.apis]
}

# ------------------------------------------------------------------------------------------------------------- red

resource "google_compute_network" "main" {
  name                    = "agrosense"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "main" {
  name                     = "agrosense-${var.region}"
  network                  = google_compute_network.main.id
  region                   = var.region
  ip_cidr_range            = local.subnet_range
  private_ip_google_access = true
}

# Cloud Run sale a la red privada (Direct VPC egress) y solo desde ella se llega al 5432 de la base.
resource "google_compute_firewall" "db_from_run" {
  name          = "agrosense-db-desde-cloud-run"
  network       = google_compute_network.main.id
  direction     = "INGRESS"
  source_ranges = [local.subnet_range]
  target_tags   = ["agrosense-db"]
  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }
}

# SSH solo por IAP (gcloud compute ssh --tunnel-through-iap), para mantenimiento.
resource "google_compute_firewall" "ssh_iap" {
  name          = "agrosense-ssh-iap"
  network       = google_compute_network.main.id
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["agrosense-db"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# ---------------------------------------------------------------------------------------------------------- secretos

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "agrosense-db-password"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db.result
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "agrosense-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

# Sin `sslmode`, la API exige SSL (`require`): la VM usa el certificado propio de Debian.
resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql://agrosense:${random_password.db.result}@${google_compute_instance.db.network_interface[0].network_ip}:5432/agrosense"
}

# ------------------------------------------------------------------------------------------------------------- base

resource "google_service_account" "db" {
  account_id   = "agrosense-db"
  display_name = "VM de la base de AgroSense"
}

resource "google_secret_manager_secret_iam_member" "db_reads_password" {
  secret_id = google_secret_manager_secret.db_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.db.email}"
}

resource "google_compute_instance" "db" {
  name         = "agrosense-db"
  machine_type = "e2-micro"
  zone         = var.zone
  tags         = ["agrosense-db"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 30
      type  = "pd-standard"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.main.id
    # IP pública efímera solo para bajar paquetes (apt). El firewall no abre el 5432 hacia afuera.
    access_config {}
  }

  service_account {
    email  = google_service_account.db.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    startup-script = file("${path.module}/db-startup.sh")
  }

  allow_stopping_for_update = true
  depends_on                = [google_secret_manager_secret_version.db_password, google_secret_manager_secret_iam_member.db_reads_password]
}

# -------------------------------------------------------------------------------------------------------- Cloud Run

resource "google_service_account" "run" {
  account_id   = "agrosense-run"
  display_name = "Cloud Run de AgroSense"
}

resource "google_secret_manager_secret_iam_member" "run_reads_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run.email}"
}

resource "google_cloud_run_v2_service" "app" {
  name                = "agrosense"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.run.email
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = 2
    }
    vpc_access {
      network_interfaces {
        network    = google_compute_network.main.id
        subnetwork = google_compute_subnetwork.main.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
    containers {
      # La imagen real la pone el workflow de despliegue (HU-235); Terraform no la toca después.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      ports {
        container_port = 8000
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        # CPU solo mientras atiende: así se cobra (y cuenta en la capa gratuita) solo el tiempo de las peticiones.
        cpu_idle          = true
        startup_cpu_boost = true
      }
      env {
        name  = "AGROSENSE_LOG_FORMAT"
        value = "json"
      }
      env {
        name  = "AGROSENSE_LOG_LEVEL"
        value = "INFO"
      }
      # Las migraciones las aplica el job `agrosense-migrate` antes de desplegar, no cada instancia al arrancar.
      env {
        name  = "AGROSENSE_AUTO_MIGRATE"
        value = "false"
      }
      dynamic "env" {
        for_each = var.web_origins == "" ? [] : [var.web_origins]
        content {
          name  = "WEB_ORIGINS"
          value = env.value
        }
      }
      env {
        name = "AGROSENSE_DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image, client, client_version, template[0].labels, template[0].revision]
  }

  depends_on = [google_project_service.apis, google_secret_manager_secret_iam_member.run_reads_url, google_secret_manager_secret_version.database_url]
}

# La app es pública: sin inicio de sesión de Google para entrar.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Las migraciones (con su copia de seguridad antes), con la misma imagen y la misma red que la app.
resource "google_cloud_run_v2_job" "migrate" {
  name                = "agrosense-migrate"
  location            = var.region
  deletion_protection = false

  template {
    task_count = 1
    template {
      service_account = google_service_account.run.email
      max_retries     = 0
      timeout         = "600s"
      vpc_access {
        network_interfaces {
          network    = google_compute_network.main.id
          subnetwork = google_compute_subnetwork.main.id
        }
        egress = "PRIVATE_RANGES_ONLY"
      }
      containers {
        image   = "us-docker.pkg.dev/cloudrun/container/job"
        command = ["python", "-m", "backend.db.migrate"]
        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }
        env {
          name  = "AGROSENSE_LOG_FORMAT"
          value = "json"
        }
        env {
          name = "AGROSENSE_DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image, client, client_version, template[0].labels]
  }

  depends_on = [google_project_service.apis, google_secret_manager_secret_iam_member.run_reads_url, google_secret_manager_secret_version.database_url]
}

# ------------------------------------------------------------------------------------- GitHub Actions (sin llaves)

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub ${var.github_repository}"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  # Solo este repositorio y solo la rama de producción.
  attribute_condition = "assertion.repository == '${var.github_repository}' && assertion.ref == 'refs/heads/${var.deploy_branch}'"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deploy" {
  account_id   = "agrosense-deploy"
  display_name = "Despliegue desde GitHub Actions"
}

resource "google_service_account_iam_member" "deploy_from_github" {
  service_account_id = google_service_account.deploy.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# Sube imágenes solo a este repositorio.
resource "google_artifact_registry_repository_iam_member" "deploy_pushes" {
  location   = var.region
  repository = google_artifact_registry_repository.app.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deploy.email}"
}

# Despliega solo este servicio y corre solo este job.
resource "google_cloud_run_v2_service_iam_member" "deploy_service" {
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.deploy.email}"
}

resource "google_cloud_run_v2_job_iam_member" "deploy_job" {
  name     = google_cloud_run_v2_job.migrate.name
  location = var.region
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.deploy.email}"
}

# Para desplegar con la cuenta de servicio de la app (actAs).
resource "google_service_account_iam_member" "deploy_acts_as_run" {
  service_account_id = google_service_account.run.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy.email}"
}

# `gcloud run deploy` lee las operaciones y las ubicaciones del proyecto.
resource "google_project_iam_member" "deploy_run_viewer" {
  project = var.project_id
  role    = "roles/run.viewer"
  member  = "serviceAccount:${google_service_account.deploy.email}"
}

# ----------------------------------------------------------------------------------------------------- presupuesto

data "google_project" "this" {}

# Avisa (no corta) por correo a los administradores de la facturación. Mide el gasto ANTES de los créditos, para saber
# a tiempo si algo se sale de la capa gratuita, mucho antes de que los créditos se acaben.
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "AgroSense producción: ${var.budget_cop} COP al mes"

  budget_filter {
    projects               = ["projects/${data.google_project.this.number}"]
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      # La cuenta de facturación es en pesos: el presupuesto va en su moneda.
      currency_code = "COP"
      units         = tostring(var.budget_cop)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }

  depends_on = [google_project_service.apis]
}
