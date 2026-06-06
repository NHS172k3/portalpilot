# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2.0"]
# ///
"""Generate a small Supabase-style TypeScript database type from metadata."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "apps" / "web" / "lib" / "db.types.ts"


def load_env() -> None:
    for filename in (".env", "apps/api/.env"):
        path = ROOT / filename
        if not path.exists():
            continue
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip(";").strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def ts_type(data_type: str, udt_name: str) -> str:
    if data_type == "ARRAY":
        return "Json[]"
    if data_type == "USER-DEFINED":
        return "string"
    if udt_name in {"int2", "int4", "int8", "float4", "float8", "numeric"}:
        return "number"
    if udt_name in {"bool"}:
        return "boolean"
    if udt_name in {"json", "jsonb"}:
        return "Json"
    return "string"


def row_shape(columns: list[dict[str, str]], *, insert: bool = False) -> str:
    lines: list[str] = ["{"]
    for column in columns:
        optional = "?" if insert and column["insert_optional"] else ""
        nullable = " | null" if column["is_nullable"] == "YES" else ""
        lines.append(f"          {column['column_name']}{optional}: {column['ts_type']}{nullable}")
    lines.append("        }")
    return "\n".join(lines)


def main() -> int:
    load_env()
    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("SUPABASE_DB_URL/DATABASE_URL missing", file=sys.stderr)
        return 1

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                  table_name,
                  column_name,
                  data_type,
                  udt_name,
                  is_nullable,
                  column_default,
                  identity_generation
                from information_schema.columns
                where table_schema = 'public'
                  and table_name in (
                    'business_profiles',
                    'attributes',
                    'documents',
                    'extracted_facts',
                    'form_definitions',
                    'form_fields',
                    'filing_tasks',
                    'recommendations',
                    'field_records',
                    'agent_events'
                  )
                order by table_name, ordinal_position
                """
            )
            rows = cur.fetchall()

    tables: dict[str, list[dict[str, str]]] = {}
    for table_name, column_name, data_type, udt_name, is_nullable, column_default, identity_generation in rows:
        tables.setdefault(table_name, []).append(
            {
                "column_name": column_name,
                "data_type": data_type,
                "udt_name": udt_name,
                "is_nullable": is_nullable,
                "ts_type": ts_type(data_type, udt_name),
                "insert_optional": is_nullable == "YES" or column_default is not None or identity_generation is not None,
            }
        )

    lines = [
        "export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];",
        "",
        "export interface Database {",
        "  public: {",
        "    Tables: {",
    ]
    for table_name in sorted(tables):
        columns = tables[table_name]
        lines.extend(
            [
                f"      {table_name}: {{",
                "        Row: " + row_shape(columns).replace("\n", "\n"),
                "        Insert: " + row_shape(columns, insert=True).replace("\n", "\n"),
                "        Update: Partial<Database['public']['Tables']['" + table_name + "']['Insert']>",
                "      }",
            ]
        )
    lines.extend(
        [
            "    }",
            "    Views: Record<string, never>",
            "    Functions: Record<string, never>",
            "    Enums: Record<string, never>",
            "    CompositeTypes: Record<string, never>",
            "  }",
            "}",
            "",
        ]
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines))
    print(f"Generated {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
