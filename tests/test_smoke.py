def test_import_package():
    import paper_triage

    assert paper_triage.__doc__


def test_tmp_db_fixture(tmp_db):
    assert tmp_db.endswith("test.db")
