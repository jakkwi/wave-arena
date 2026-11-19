"""Monthly cost budget with an email alert at 5 USD (issue #12, ADR 0006).

A budget only alerts, it never stops spending. The stage throttling in api.py is what bounds
the cost; the budget is the alarm that says something is wrong.
"""

import aws_cdk as cdk
from aws_cdk import aws_budgets as budgets
from constructs import Construct

MONTHLY_LIMIT_USD = 5
# (type, percent of the limit). ACTUAL 100 is the 5 USD alert. ACTUAL 20 (1 USD) is the early
# warning: normal use stays near zero, and FORECASTED needs cost history a new account lacks.
NOTIFICATIONS = (("ACTUAL", 20), ("ACTUAL", 100), ("FORECASTED", 100))
# A rough shape check only: a typo in the address means alerts silently go nowhere.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def budget_email_parameter(scope: Construct) -> cdk.CfnParameter:
    """The alert address is supplied at deploy time, so no real address lives in the repo."""
    return cdk.CfnParameter(
        scope,
        "BudgetEmail",
        type="String",
        allowed_pattern=EMAIL_PATTERN,
        constraint_description="must be an email address",
        description="Email address for the monthly cost budget alert",
    )


def monthly_cost_budget(scope: Construct, email: cdk.CfnParameter) -> budgets.CfnBudget:
    """Account-wide, not filtered by the project tag: an untagged or forgotten resource would
    slip past a tag filter, and this account exists for this project."""
    subscriber = budgets.CfnBudget.SubscriberProperty(
        subscription_type="EMAIL", address=email.value_as_string
    )
    return budgets.CfnBudget(
        scope,
        "MonthlyCostBudget",
        budget=budgets.CfnBudget.BudgetDataProperty(
            budget_type="COST",
            time_unit="MONTHLY",
            budget_limit=budgets.CfnBudget.SpendProperty(amount=MONTHLY_LIMIT_USD, unit="USD"),
        ),
        notifications_with_subscribers=[
            budgets.CfnBudget.NotificationWithSubscribersProperty(
                notification=budgets.CfnBudget.NotificationProperty(
                    notification_type=notification_type,
                    comparison_operator="GREATER_THAN",
                    threshold=threshold_percent,
                    threshold_type="PERCENTAGE",
                ),
                subscribers=[subscriber],
            )
            for notification_type, threshold_percent in NOTIFICATIONS
        ],
    )
