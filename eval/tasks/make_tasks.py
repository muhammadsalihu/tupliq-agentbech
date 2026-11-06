"""Generate the eval task set: API contract breaking-change detection.

Each task gives the model two versions of a REST API contract and a list of
changes between them. The model must label every change as "breaking" or
"non-breaking" for existing API clients. Ground truth was set by expert
judgment (see README for the decision rules).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "tasks")  # eval/tasks

# Reusable minimal API spec: dict of path -> method -> spec
def op(summary, params, required_params, request_fields, response_fields):
    return {
        "summary": summary,
        "parameters": [{"name": p, "type": t} for p, t in params],
        "required_parameters": required_params,
        "request_body": request_fields,
        "response_body": response_fields,
    }


def spec_v1():
    return {
        "base_url": "https://api.example.com/v1",
        "paths": {
            "/orders": {
                "GET": op("List orders", [("limit", "integer"), ("cursor", "string")],
                          [], None,
                          {"orders": "array", "next_cursor": "string"}),
                "POST": op("Create order", [], [],
                           {"amount": "number", "currency": "string",
                            "customer_id": "string", "note": "string"},
                           {"id": "string", "status": "string", "amount": "number"}),
            },
            "/orders/{id}": {
                "GET": op("Get order", [("id", "string")], ["id"], None,
                          {"id": "string", "status": "string", "amount": "number",
                           "note": "string"}),
                "DELETE": op("Cancel order", [("id", "string")], ["id"], None,
                             {"deleted": "boolean"}),
            },
            "/customers/{id}": {
                "GET": op("Get customer", [("id", "string")], ["id"], None,
                          {"id": "string", "email": "string", "name": "string"}),
            },
        },
    }


def spec_v2_changes():
    """Six tasks, each applying one set of changes to the same base spec."""
    return [
        ("task_01", "Remove a response field",
         "Remove `note` from the GET /orders/{id} response body.",
         lambda s: s["paths"]["/orders/{id}"]["GET"]["response_body"].pop("note"),
         {"C1": "breaking"},
         "Removing a response field breaks clients that read it."),
        ("task_02", "Add an optional response field",
         "Add `created_at` (string, ISO-8601) to the GET /orders/{id} response body.",
         lambda s: s["paths"]["/orders/{id}"]["GET"]["response_body"].update(
             {"created_at": "string"}),
         {"C1": "non-breaking"},
         "Adding a response field does not break clients that ignore unknown fields."),
        ("task_03", "Make an optional request field required",
         "Make `note` a required request field on POST /orders.",
         lambda s: s["paths"]["/orders"]["POST"]["required_parameters"].append("note"),
         {"C1": "breaking"},
         "Requiring a previously optional input breaks clients that omit it."),
        ("task_04", "Rename a parameter",
         "Rename the `cursor` query parameter on GET /orders to `page`.",
         lambda s: (s["paths"]["/orders"]["GET"]["parameters"].pop(1),
                    s["paths"]["/orders"]["GET"]["parameters"].append(
                        {"name": "page", "type": "string"})),
         {"C1": "breaking"},
         "Renaming a parameter breaks clients using the old name."),
        ("task_05", "Narrow a numeric type",
         "Change `amount` from `number` (any decimal) to `integer` everywhere it appears.",
         lambda s: [s["paths"]["/orders"]["POST"]["request_body"].__setitem__("amount", "integer"),
                    s["paths"]["/orders"]["GET"]["response_body"].__setitem__("amount", "integer"),
                    s["paths"]["/orders/{id}"]["GET"]["response_body"].__setitem__("amount", "integer")],
         {"C1": "breaking"},
         "Narrowing number to integer rejects decimal values clients may send."),
        ("task_06", "Change a response field's semantics",
         "In GET /orders/{id}, change `status` from an enum of "
         "(pending, paid, cancelled) to (pending, paid, cancelled, refunded). "
         "Nothing else changes.",
         lambda s: None,
         {"C1": "non-breaking"},
         "Adding a new enum value breaks clients with exhaustive switches, but "
         "per the eval's stated contract rule (JSON API, unknown values treated "
         "as data, no client-side enum narrowing declared), this is non-breaking."),
    ]


def build():
    os.makedirs(OUT, exist_ok=True)
    for tid, title, change_text, mutate, gt, rationale in spec_v2_changes():
        old = spec_v1()
        new = spec_v1()
        mutate(new)
        task = {
            "id": tid,
            "title": title,
            "domain": "REST API versioning",
            "instructions": (
                "You are reviewing an API contract change for backward "
                "compatibility. Existing clients are JSON API consumers that "
                "tolerate unknown response fields but send exactly the fields "
                "they were built against. For each change below, label it "
                "\"breaking\" if it can cause an existing client integration "
                "to fail, otherwise \"non-breaking\". "
                "Reply with ONLY a JSON object mapping change IDs to "
                "\"breaking\" or \"non-breaking\"."
            ),
            "changes": [{"id": k, "description": change_text} for k in gt],
            "old_spec": old,
            "new_spec": new,
            "ground_truth": gt,
            "ground_truth_rationale": rationale,
        }
        path = os.path.join(OUT, f"{tid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(task, f, indent=2)
        print("wrote", path)


if __name__ == "__main__":
    build()
