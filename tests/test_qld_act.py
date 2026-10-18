from clausewise.ingest.qld_act import act_meta, parse_act

# Trimmed from the real page, including its quirks: unclosed <p>, uppercase tags, a history
# note to drop, a statutory note to keep.
HTML = """
<div id="fragview"><div class="content"><p class="LongTitleParagraph">
<div class="ChapterHeadingParagraph"><p class="ChapterHeadingParagraph"><a name="ch.3"></a>
<span class="HeadingNumber">Chapter 3</span> <b><span class="HeadingName">Rights</span></b></p></div>
<div class="PartHeadingParagraph"><p class="PartHeadingParagraph"><a name="ch.3-pt.2"></a>
<span class="HeadingNumber">Part 2</span> <b><span class="PartHeadingName">Standard</span></b></p></div>
<P class="HeadingParagraph"><a name="sec.185"></a><B class="HeadingStyle">185</B><span class="HeadingName">Lessor&#8217;s obligations</span></P>
<BLOCKQUOTE class="FlatParagraph"><BLOCKQUOTE class="Paragraph"><span class="ListNumber">(1)</span>At the start, the lessor must ensure&#8212;<BLOCKQUOTE class="Paragraph List"><span class="ListNumber">(a)</span>the premises are clean; and</BLOCKQUOTE>
<BLOCKQUOTE class="Paragraph List"><span class="ListNumber">(b)</span>fit to live in.</BLOCKQUOTE>
</BLOCKQUOTE><BLOCKQUOTE class="Paragraph"><span class="ListNumber">(2)</span>While the tenancy continues, the lessor must maintain the premises.</BLOCKQUOTE>
<P class="note"><A NAME="sec.185-ssec.2-note"></A><span class="NoteHeadingName">Note&#8212;</span></P><BLOCKQUOTE class="note">See <a href="#sec.217">section&#160;217</a>.</BLOCKQUOTE>
<BLOCKQUOTE class="view-history-note history-note"><P class="view-history-note">amd 2024 No. 5 s 10</P></BLOCKQUOTE>
</BLOCKQUOTE>
</div></div>
"""


def test_section_has_path_anchor_and_ordered_lines():
    [chunk] = parse_act(HTML)
    assert chunk.heading_path == "Chapter 3 Rights > Part 2 Standard > s 185 Lessor’s obligations"
    assert chunk.anchor == "sec.185"
    assert chunk.body.splitlines() == [
        "(1) At the start, the lessor must ensure—",
        "(a) the premises are clean; and",
        "(b) fit to live in.",
        "(2) While the tenancy continues, the lessor must maintain the premises.",
        "Note—",
        "See section 217.",
    ]
    assert "amd 2024" not in chunk.body


def test_act_meta_reads_in_force_date():
    view = '<a href="/view/whole/html/inforce/2026-08-17/act-2008-073" class="btn">'
    meta = act_meta(view, "RTRA Act 2008", "act-2008-073")
    assert meta.version_date == "2026-08-17"
    assert meta.base_url.endswith("/inforce/2026-08-17/act-2008-073")
