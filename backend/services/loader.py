import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from llama_index.core import Document

# --- Section header: "### NAME"
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$")

# --- Claims headers: [Claim 1] or [Claim 1-2]
CLAIM_RE = re.compile(r"^\[Claim\s+(\d+)(?:-(\d+))?\]\s*$", re.IGNORECASE)

# --- Generic chunk tags inside sections: [SP 1], [TF 2], [EOI 3] ...
CHUNK_TAG_RE = re.compile(r"^\[([A-Z]{1,6})\s+(\d+)\]\s*$")


DOC_META_KV_RE = re.compile(r"^\s*([A-Za-z0-9 _]+?)\s*:\s*(.+?)\s*$")

def parse_doc_meta(doc_meta_text: str) -> Dict[str, str]:
    """
    DOC_META 예:
      Application Date: 20200101
      Application Number: 10-2020-xxxxx
      Open Date: 20210101
      Open Number: 10-2021-xxxxx
    """
    out: Dict[str, str] = {}
    for line in doc_meta_text.splitlines():
        m = DOC_META_KV_RE.match(line)
        if not m:
            continue
        k = m.group(1).strip().lower().replace(" ", "_")  # application_number
        v = m.group(2).strip()
        out[k] = v
    return out



def split_sections(text: str) -> List[Tuple[str, str]]:
    lines = text.splitlines()
    sections: List[Tuple[str, List[str]]] = []
    cur_name: Optional[str] = None
    cur_buf: List[str] = []

    def flush():
        nonlocal cur_name, cur_buf
        if cur_name is not None:
            while cur_buf and not cur_buf[0].strip():
                cur_buf.pop(0)
            while cur_buf and not cur_buf[-1].strip():
                cur_buf.pop()
            if cur_buf:
                sections.append((cur_name, cur_buf))
        cur_name = None
        cur_buf = []

    for line in lines:
        m = SECTION_RE.match(line)
        if m:
            flush()
            cur_name = m.group(1).strip()
            continue
        if cur_name is None:
            continue
        cur_buf.append(line)

    flush()
    return [(name, "\n".join(buf).strip()) for name, buf in sections if "\n".join(buf).strip()]


def split_paragraphs(section_text: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n+", section_text) if p.strip()]


def split_claims(claims_text: str) -> List[Tuple[int, Optional[int], str]]:
    lines = claims_text.splitlines()
    out: List[Tuple[int, Optional[int], List[str]]] = []
    cur_no: Optional[int] = None
    cur_sub: Optional[int] = None
    cur_buf: List[str] = []

    def flush():
        nonlocal cur_no, cur_sub, cur_buf
        if cur_no is not None:
            txt = "\n".join(cur_buf).strip()
            if txt:
                out.append((cur_no, cur_sub, txt))
        cur_no, cur_sub, cur_buf = None, None, []

    for line in lines:
        m = CLAIM_RE.match(line.strip())
        if m:
            flush()
            cur_no = int(m.group(1))
            cur_sub = int(m.group(2)) if m.group(2) is not None else None
            continue
        if cur_no is None:
            continue
        cur_buf.append(line)

    flush()
    return [(no, sub, txt) for (no, sub, txt) in out]


def split_by_chunk_tags(section_text: str) -> List[Tuple[str, int, str]]:
    lines = section_text.splitlines()
    out: List[Tuple[str, int, List[str]]] = []
    cur_tag: Optional[str] = None
    cur_no: Optional[int] = None
    cur_buf: List[str] = []
    found_any = False

    def flush():
        nonlocal cur_tag, cur_no, cur_buf
        if cur_tag is not None and cur_no is not None:
            txt = "\n".join(cur_buf).strip()
            if txt:
                out.append((cur_tag, cur_no, txt))
        cur_tag, cur_no, cur_buf = None, None, []

    for line in lines:
        m = CHUNK_TAG_RE.match(line.strip())
        if m:
            found_any = True
            flush()
            cur_tag = m.group(1).upper()
            cur_no = int(m.group(2))
            continue
        if cur_tag is None:
            continue
        cur_buf.append(line)

    flush()
    if not found_any:
        return []
    return [(t, n, txt) for (t, n, txt) in out]


def load_txt_as_docs(txt_path: str) -> List[Document]:
    p = Path(txt_path)
    raw = p.read_text(encoding="utf-8", errors="ignore")
    sections = split_sections(raw)

    # DOC_META에서 번호 추출
    doc_meta_map: Dict[str, str] = {}
    for name, body in sections:
        if name.strip().upper() == "DOC_META":
            doc_meta_map = parse_doc_meta(body)
            break

    application_number = doc_meta_map.get("application_number")
    open_number = doc_meta_map.get("open_number")

    # --- DOC_META에서 Applicant / Inventor / Agent 수집 ---
    applicants: List[str] = []
    inventors: List[str] = []
    agents: List[str] = []

    for name, body in sections:
        if name.strip().upper() != "DOC_META":
            continue

        for line in body.splitlines():
            line = line.strip()
            if line.lower().startswith("applicant"):
                _, v = line.split(":", 1)
                applicants.append(v.strip())
            elif line.lower().startswith("inventor"):
                _, v = line.split(":", 1)
                inventors.append(v.strip())
            elif line.lower().startswith("agent"):
                _, v = line.split(":", 1)
                agents.append(v.strip())
        break


    # "특허번호로 쓸 값" 결정: 공개번호 
    patent_no = open_number


    # Extract TITLE (라인 형식: TITLE: ...)
    title = ""
    for line in raw.splitlines():
        if line.strip().upper().startswith("TITLE:"):
            title = line.split(":", 1)[1].strip()
            break

    base_meta: Dict[str, object] = {
        "source": str(p),
        "title": title or None,
        "patent_no": patent_no or None,
        "application_number": application_number or None,
        "application_date": doc_meta_map.get("application_date") or None,
        "open_date": doc_meta_map.get("open_date") or None,
        "applicants": applicants or None,
        "inventors": inventors or None,
        "agents": agents or None,
    }

    def norm_section(name: str) -> str:
        return name.strip().lower().replace(" ", "_")

    docs: List[Document] = []

    for sec_name, sec_body in sections:
        sec_upper = sec_name.strip().upper()
        sec_norm = norm_section(sec_name)

        # DOC_META
        if sec_upper == "DOC_META":
            docs.append(
                Document(
                    text=sec_body,
                    metadata={**base_meta, "section": "doc_meta"},
                )
            )
            continue

        # ABSTRACT
        if sec_upper == "ABSTRACT":
            docs.append(
                Document(
                    text=sec_body,
                    metadata={**base_meta, "section": "abstract"},
                )
            )
            continue

        # CLAIMS: split by [Claim n] / [Claim n-m]
        if sec_upper == "CLAIMS":
            for claim_no, sub_no, claim_txt in split_claims(sec_body):
                header = f"[CLAIM {claim_no}]" if sub_no is None else f"[CLAIM {claim_no}-{sub_no}]"
                meta = {**base_meta, "section": "claim", "claim_no": claim_no}
                if sub_no is not None:
                    meta["sub_no"] = sub_no

                docs.append(
                    Document(
                        text=claim_txt,
                        metadata=meta,
                    )
                )
            continue

        # Other sections: if chunk tags exist ([SP 1], [TF 2] ...), split by them first
        chunks = split_by_chunk_tags(sec_body)
        if chunks:
            for tag, no, txt in chunks:
                docs.append(
                    Document(
                        text=txt,
                        metadata={**base_meta, "section": sec_norm, "chunk_tag": tag, "chunk_no": no},
                    )
                )
            continue

        # Fallback: paragraph split if blank lines exist; else whole section
        paras = split_paragraphs(sec_body)
        if len(paras) <= 1:
            docs.append(
                Document(
                    text=sec_body,
                    metadata={**base_meta, "section": sec_norm},
                )
            )
        else:
            for i, para in enumerate(paras, start=1):
                docs.append(
                    Document(
                        text=para,
                        metadata={**base_meta, "section": sec_norm, "para_no": i},
                    )
                )

    return docs
