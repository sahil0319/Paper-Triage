"""Writes sample.pdf: a 3-page fixture PDF (stdlib only, raw PDF objects).

Run: python src/paper_triage/fixtures/make_sample_pdf.py
Page 1 is the original single-page sample. Page 2 holds the marker word "Quartzite" and page 3
holds "Obsidian"; tests use them to check page-level citations.
"""

from pathlib import Path

TITLE = "Sample Paper on Diffusion Distillation"

PAGES = [
    [
        "Sample Paper on Diffusion Distillation",
        "Abstract. We study distillation of diffusion models into few-step generators.",
        "Our method reduces sampling cost by a factor of eight while keeping image quality.",
        "1 Introduction",
        "Diffusion models produce high quality samples but require many network evaluations.",
        "Distillation compresses the sampling trajectory into a small number of steps.",
        "We propose a progressive scheme that halves the number of steps at every stage.",
        "2 Method",
        "A student network is trained to match two teacher steps with one student step.",
        "The procedure is repeated until the student needs only four steps in total.",
        "3 Experiments",
        "We evaluate on ImageNet and report FID against the undistilled teacher baseline.",
        "The distilled model achieves an eight times speedup with a small FID increase.",
        "Ablations show that the loss weighting matters more than the schedule choice.",
        "4 Conclusion",
        "Progressive distillation offers a simple recipe for fast sampling from diffusion models.",
        "References",
        "[1] Ho et al. Denoising diffusion probabilistic models.",
    ],
    [
        "5 Analysis",
        "We inspect the sampled latents layer by layer to see where the student departs.",
        "Quartzite filters remove the high frequency residue left by the one step student.",
        "The filter is applied once per stage and adds no trainable parameters.",
        "Table 2 lists the measured error for each stage of the progressive schedule.",
    ],
    [
        "6 Limitations",
        "The approach was tested on one dataset and one teacher architecture only.",
        "Obsidian checkpoints from the final stage are released for later comparison.",
        "We did not study text conditioned models or video generation in this work.",
        "7 Acknowledgements",
        "The authors thank the reviewers for their careful reading of the draft.",
    ],
]


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(lines: list[str]) -> bytes:
    body = "BT /F1 11 Tf 14 TL 50 740 Td\n" + "".join(f"({_esc(t)}) Tj T*\n" for t in lines) + "ET"
    data = body.encode("latin-1")
    return b"<< /Length %d >>\nstream\n%s\nendstream" % (len(data), data)


def build() -> bytes:
    # object numbers: 1 catalog, 2 pages, 3 page 1, 4 content 1, 5 font, 6 info, then page/content
    n = len(PAGES)
    page_ids = [3] + [7 + 2 * i for i in range(n - 1)]
    content_ids = [4] + [8 + 2 * i for i in range(n - 1)]
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [%s] /Count %d >>"
        % (" ".join(f"{p} 0 R" for p in page_ids).encode(), n),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: b"<< /Title (%s) >>" % _esc(TITLE).encode(),
    }
    for pid, cid, lines in zip(page_ids, content_ids, PAGES, strict=True):
        objs[pid] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
            b"/Resources << /Font << /F1 5 0 R >> >> >>" % cid
        )
        objs[cid] = _stream(lines)
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (num, objs[num])
    xref = len(out)
    size = max(objs) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for num in range(1, size):
        out += b"%010d 00000 n \n" % offsets[num]
    out += b"trailer\n<< /Size %d /Root 1 0 R /Info 6 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (size, xref)
    return bytes(out)


if __name__ == "__main__":
    target = Path(__file__).with_name("sample.pdf")
    target.write_bytes(build())
    print(f"wrote {target} ({target.stat().st_size} bytes)")
