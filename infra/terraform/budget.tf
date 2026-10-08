# Expected spend is $1-4 a month (ADR-0014); an alert means something is wrong.
resource "google_billing_budget" "monthly" {
  billing_account = var.billing_account
  display_name    = "budget-planner production"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      units = tostring(var.budget_amount)
    }
  }

  threshold_rules {
    threshold_percent = 0.25
  }
  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 1.0
  }

  depends_on = [google_project_service.this]
}
