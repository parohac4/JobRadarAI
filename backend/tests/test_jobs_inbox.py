from app.services.jobs import inbox_filter_clause


def test_inbox_clause_builds_for_all_tabs():
    for tab in ("active", "snoozed", "dismissed"):
        sql = str(inbox_filter_clause(tab).compile(compile_kwargs={"literal_binds": True}))
        assert "inbox_status" in sql
