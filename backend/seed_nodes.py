"""Seed Node Definitions for FlowAlchemy.

Run: python seed_nodes.py
"""

from app.core.database import SessionLocal
from app.models.workflow import NodeDefinition

NODE_DEFINITIONS = [
    {
        "node_type": "trigger",
        "name": "Trigger",
        "description": "Entry point for workflow execution. Can be manual, scheduled, or webhook-triggered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger_type": {
                    "type": "string",
                    "enum": ["manual", "schedule", "webhook"],
                    "default": "manual",
                    "description": "How this workflow is triggered"
                },
                "webhook_url": {
                    "type": "string",
                    "description": "Webhook URL (only for webhook trigger)"
                }
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "triggered_at": {"type": "string", "format": "date-time"},
                "trigger_data": {"type": "object"}
            }
        },
        "icon": "Play",
        "category": "trigger",
        "is_premium": False,
    },
    {
        "node_type": "http_request",
        "name": "HTTP Request",
        "description": "Send HTTP requests to external APIs. Supports GET, POST, PUT, DELETE, PATCH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Request URL"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "default": "GET",
                    "description": "HTTP method"
                },
                "headers": {
                    "type": "object",
                    "description": "Request headers"
                },
                "body": {
                    "type": "object",
                    "description": "Request body (for POST/PUT/PATCH)"
                },
                "timeout": {
                    "type": "integer",
                    "default": 30000,
                    "description": "Request timeout in milliseconds"
                }
            },
            "required": ["url"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "integer"},
                "data": {"type": "object"},
                "headers": {"type": "object"}
            }
        },
        "icon": "Globe",
        "category": "integration",
        "is_premium": False,
    },
    {
        "node_type": "transform",
        "name": "Transform",
        "description": "Transform data using filter, map, merge, or split operations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Input data to transform"
                },
                "operation": {
                    "type": "string",
                    "enum": ["identity", "filter", "map", "merge", "split"],
                    "description": "Transformation operation"
                },
                "params": {
                    "type": "object",
                    "description": "Operation parameters"
                }
            },
            "required": ["operation"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "object"}
            }
        },
        "icon": "Shuffle",
        "category": "logic",
        "is_premium": False,
    },
    {
        "node_type": "condition",
        "name": "Condition",
        "description": "Branch workflow based on conditions. Supports if/else logic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Data to evaluate"
                },
                "condition": {
                    "type": "string",
                    "description": "Condition expression (e.g., 'data.status === 200')"
                },
                "operator": {
                    "type": "string",
                    "enum": ["equals", "not_equals", "greater_than", "less_than", "greater_equal", "less_equal", "contains", "not_contains", "starts_with", "ends_with", "is_empty", "is_not_empty"],
                    "description": "Comparison operator"
                },
                "value": {
                    "description": "Value to compare against"
                }
            },
            "required": ["condition"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "boolean"},
                "data": {"type": "object"}
            }
        },
        "icon": "GitBranch",
        "category": "logic",
        "is_premium": False,
    },
    {
        "node_type": "delay",
        "name": "Delay",
        "description": "Wait for a specified duration before continuing execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_ms": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Delay duration in milliseconds"
                },
                "data": {
                    "type": "object",
                    "description": "Data to pass through"
                }
            },
            "required": ["duration_ms"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "data": {"type": "object"},
                "delayed_at": {"type": "string", "format": "date-time"}
            }
        },
        "icon": "Clock",
        "category": "utility",
        "is_premium": False,
    },
    {
        "node_type": "output",
        "name": "Output",
        "description": "Send results to external services (webhook, email, Slack).",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "Data to send"
                },
                "destination": {
                    "type": "string",
                    "enum": ["webhook", "email", "slack"],
                    "description": "Output destination"
                },
                "config": {
                    "type": "object",
                    "description": "Destination-specific configuration"
                }
            },
            "required": ["destination"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "sent_at": {"type": "string", "format": "date-time"}
            }
        },
        "icon": "Send",
        "category": "integration",
        "is_premium": False,
    },
]


def seed_node_definitions():
    db = SessionLocal()
    try:
        for node_data in NODE_DEFINITIONS:
            existing = db.query(NodeDefinition).filter(
                NodeDefinition.node_type == node_data["node_type"]
            ).first()

            if existing:
                print(f"  SKIP: {node_data['node_type']} (already exists)")
                continue

            node_def = NodeDefinition(**node_data)
            db.add(node_def)
            print(f"  CREATE: {node_data['node_type']}")

        db.commit()
        print("\nDone! Node definitions seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding Node Definitions...")
    seed_node_definitions()
