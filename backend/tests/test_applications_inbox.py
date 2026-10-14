from app.services.applications import application_inbox_clause


def test_application_inbox_clause_builds():
    for tab in ("active", "snoozed"):
        sql = str(application_inbox_clause(tab).compile(compile_kwargs={"literal_binds": True}))
        assert "next_action_at" in sql
