from __future__ import annotations

from app.schemas.blockers import ParsedDocument, ValidationIssue, ValidationResult


def _issue(code: str, path: str, message: str, severity: str, suggested_fix: str) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        path=path,
        message=message,
        severity=severity,  # type: ignore[arg-type]
        suggested_fix=suggested_fix,
    )


def validate_document(document: ParsedDocument, max_individual_weight: float = 60.0) -> ValidationResult:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    mandatory_fields = [
        ("title", document.title),
        ("credits", document.credits),
        ("objectives", document.objectives),
        ("bibliography", document.bibliography),
        ("evaluation", document.evaluation),
        ("competencies", document.competencies),
    ]

    for field_name, value in mandatory_fields:
        missing = value is None or value == [] or (isinstance(value, str) and not value.strip())
        if missing:
            errors.append(
                _issue(
                    code="MISSING_FIELD",
                    path=field_name,
                    message=f"Mandatory field '{field_name}' is missing",
                    severity="error",
                    suggested_fix=f"Complete section '{field_name}' in the source document.",
                )
            )

    if document.bibliography is not None and len(document.bibliography) == 0:
        errors.append(
            _issue(
                code="EMPTY_BIBLIOGRAPHY",
                path="bibliography",
                message="Bibliography is empty",
                severity="error",
                suggested_fix="Add at least one bibliography reference.",
            )
        )

    if document.evaluation:
        weights = [item.weight for item in document.evaluation if item.weight is not None]
        weight_sum = sum(weights)
        if abs(weight_sum - 100.0) > 0.001:
            errors.append(
                _issue(
                    code="EVAL_SUM_NOT_100",
                    path="evaluation",
                    message=f"Evaluation weights sum is {weight_sum:.2f}, expected 100",
                    severity="error",
                    suggested_fix="Adjust evaluation percentages so total is exactly 100.",
                )
            )

        for idx, item in enumerate(document.evaluation):
            if item.weight is not None and item.weight > max_individual_weight:
                warnings.append(
                    _issue(
                        code="EVAL_WEIGHT_ABOVE_LIMIT",
                        path=f"evaluation[{idx}]",
                        message=(
                            f"Evaluation item '{item.label}' has {item.weight:.2f}% "
                            f"(limit {max_individual_weight:.2f}%)"
                        ),
                        severity="warning",
                        suggested_fix="Redistribute the exceeding percentage to other evaluation items.",
                    )
                )

    return ValidationResult(errors=errors, warnings=warnings)
