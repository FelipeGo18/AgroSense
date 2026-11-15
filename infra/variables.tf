variable "project_id" {
  description = "Proyecto de Google Cloud de producción."
  type        = string
  default     = "agrosense-prod-2026"
}

variable "region" {
  description = "Región de Cloud Run y de la VM de la base. us-east1 entra en la capa gratuita de Compute Engine."
  type        = string
  default     = "us-east1"
}

variable "zone" {
  description = "Zona de la VM de la base (e2-micro gratis solo en us-east1, us-central1 o us-west1)."
  type        = string
  default     = "us-east1-b"
}

variable "github_repository" {
  description = "Repositorio que puede desplegar con Workload Identity Federation (dueño/nombre)."
  type        = string
  default     = "FelipeGo18/AgroSense"
}

variable "github_repository_id" {
  description = "El identificador numérico del repositorio (`gh api repos/FelipeGo18/AgroSense --jq .id`): no cambia si lo renombran, y uno nuevo con el mismo nombre tiene otro."
  type        = string
  default     = "1413323171"
}

variable "deploy_branch" {
  description = "La única rama que despliega a producción."
  type        = string
  default     = "produccion"
}

variable "min_instances" {
  description = "Instancias calientes de Cloud Run. 0 es gratis; 1 durante el juzgamiento para que no haya arranque en frío (sale del crédito)."
  type        = number
  default     = 0
}

variable "web_origins" {
  description = "Orígenes extra que pueden cambiar datos (CSRF), separados por coma: el dominio propio cuando exista (HU-236). El de Cloud Run ya es el propio."
  type        = string
  default     = ""
}

variable "billing_account" {
  description = "Cuenta de facturación del proyecto (la de los créditos). Va en `terraform.tfvars`, fuera de git: es de una persona y el repositorio es público (`terraform.tfvars.example`)."
  type        = string
}

variable "budget_cop" {
  description = "Presupuesto mensual en pesos (la moneda de la cuenta), unos 10 USD: avisa por correo al 50, 90 y 100 %."
  type        = number
  default     = 40000
}
