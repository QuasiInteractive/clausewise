from clausewise.ingest.chunk import chunk_markdown


def test_heading_path_tracks_nesting():
    text = """# Part 5 Obligations
## Division 2 Landlord
### 185 Landlord's obligations
The lessor must maintain the premises in good repair.
## Division 3 Tenant
### 188 Tenant's obligations
The tenant must keep the premises clean.
"""
    chunks = chunk_markdown(text)
    assert [c.heading_path for c in chunks] == [
        "Part 5 Obligations > Division 2 Landlord > 185 Landlord's obligations",
        "Part 5 Obligations > Division 3 Tenant > 188 Tenant's obligations",
    ]
    assert chunks[0].body == "The lessor must maintain the premises in good repair."


def test_empty_sections_are_dropped():
    chunks = chunk_markdown("# A\n\n# B\nbody")
    assert [(c.heading_path, c.body) for c in chunks] == [("B", "body")]


def test_long_section_splits_on_paragraphs_and_keeps_heading():
    paragraphs = [f"Paragraph {i} " + "x" * 80 for i in range(10)]
    text = "# s 1\n" + "\n\n".join(paragraphs)
    chunks = chunk_markdown(text, max_chars=300)
    assert len(chunks) > 1
    assert all(c.heading_path == "s 1" for c in chunks)
    assert all(len(c.body) <= 300 for c in chunks)
    # nothing lost, nothing duplicated
    joined = "\n\n".join(c.body for c in chunks)
    assert joined == "\n\n".join(paragraphs)


def test_long_paragraph_splits_on_lines_before_sentences():
    lines = [f"({i}) The lessor must do thing number {i}. Then another sentence." for i in range(20)]
    text = "# s 3\n" + "\n".join(lines)
    chunks = chunk_markdown(text, max_chars=250)
    assert len(chunks) > 1
    # every line survives intact; none were glued together or cut mid-line
    assert [line for c in chunks for line in c.body.splitlines()] == lines


def test_oversized_paragraph_splits_on_sentences():
    sentence = "The tenant must give notice. "
    text = "# s 2\n" + sentence * 40
    chunks = chunk_markdown(text, max_chars=200)
    assert len(chunks) > 1
    assert all(len(c.body) <= 200 for c in chunks)
    assert all(c.body.startswith("The tenant") for c in chunks)
