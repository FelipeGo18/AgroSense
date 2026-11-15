# El estado de Terraform en Cloud Storage, no en un computador: cualquiera de los responsables puede hacer `plan` y
# `apply`, y no se pierde con la máquina. Trae la clave de la base: el bucket es privado y guarda versiones.
# Se crea una sola vez, a mano, antes que todo lo demás (`backend/README.md`, «Producción en Google Cloud»).
terraform {
  backend "gcs" {
    bucket = "agrosense-prod-2026-tfstate"
    prefix = "infra"
  }
}
