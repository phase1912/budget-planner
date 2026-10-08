variable "project_id" {
  description = "Google Cloud project that hosts production (ADR-0014)."
  type        = string
}

variable "billing_account" {
  description = "Billing account the budget alert watches, e.g. 016F8F-XXXXXX-XXXXXX."
  type        = string
}

variable "region" {
  description = "Region for everything regional. The free tiers apply only in us-west1, us-central1 and us-east1."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zone of the database VM."
  type        = string
  default     = "us-central1-a"
}

variable "app_engine_location" {
  description = "App Engine location for the mail relay; App Engine names us-central1 'us-central'. Cannot be changed once created."
  type        = string
  default     = "us-central"
}

variable "github_repository" {
  description = "owner/name of the repository whose main branch may deploy."
  type        = string
  default     = "phase1912/budget-planner"
}

variable "hosting_site_id" {
  description = "Firebase Hosting site id; the frontend is served at https://<id>.web.app. Globally unique."
  type        = string
  default     = "budget-agent-phase1912"
}

variable "backend_image" {
  description = "Image the backend service starts with. Deploys replace it; Terraform then leaves it alone."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "llm_model" {
  description = "LiteLLM model string for every AI feature (ADR-0006, ADR-0014)."
  type        = string
  default     = "vertex_ai/gemini-2.5-flash"
}

variable "budget_amount" {
  description = "Monthly budget in the billing account's own currency; alerts fire at 25%, 50% and 100%."
  type        = number
  default     = 20
}
