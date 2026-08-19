---
trigger: always_on
---

# Diagram Handling Rules . draw.io / diagrams.net Files  
`diagramming-draw.io-md`

These rules define safe, deterministic, and failure-resistant handling of diagram files created with **draw.io / diagrams.net**, especially large or complex diagrams. The goals are correctness, reversibility, structural integrity, and predictable rendering.

---

## What draw.io Files Are

- `.draw.io` files are **text-based XML documents**.
- They typically contain:
  - An `<mxfile>` root element
  - One or more `<diagram>` elements
  - Embedded **mxGraphModel** XML
- Files may be:
  - Plain XML
  - Compressed XML (base64 + deflate) when exported in certain modes

Important constraints:
- draw.io files are **data structures**, not free-form markup.
- Small structural errors will break rendering.
- Ordering, IDs, and attributes are critical.

Agents MUST treat draw.io files as **structured data**, not prose.

---

## Supported File Variants

Agents MUST detect the file variant before editing:

- Plain XML draw.io file
- Compressed draw.io file (base64 + deflate)
- Embedded draw.io XML inside another container

If compression is detected:
- Decompress to plain XML in a temporary directory
- Operate only on the decompressed form
- Recompress only after validation

---

## When to Use draw.io

Agents SHOULD create or modify `.draw.io` files when:
- A workflow, architecture, dependency graph, or system diagram is required
- Visual structure is more expressive than text
- The user explicitly requests a diagram

Agents MUST NOT replace diagrams with text unless explicitly instructed.

---

## Rules for Creating draw.io Files

When generating new `.draw.io` files:

- Always produce **valid mxGraph XML**
- Include:
  - `<mxfile>` root
  - At least one `<diagram>` element
  - `<mxGraphModel>` with required attributes
- Use deterministic IDs
- Maintain consistent layout geometry

Agents MUST:
- Prefer simple shapes and connectors
- Avoid unnecessary styling
- Ensure all elements are visible within the canvas bounds

---

## Rules for Editing draw.io Files

### Pre-edit Analysis

Before editing:
- Validate XML well-formedness
- Identify:
  - Number of diagrams
  - Total line count
  - Compression state
- Back up the original file

Agents MUST NOT:
- Reformat XML arbitrarily
- Change IDs unless required
- Reorder nodes without intent

---

## Large draw.io File Handling

Large draw.io files are fragile and prone to corruption if edited monolithically.

### Chunking Rules

If a draw.io file exceeds safe thresholds (line count or size):

1. Create a temporary workspace:
   - `/tmp/windsurf/<operation-id>/`
2. Split the XML into **logical chunks**, not arbitrary slices:
   - Per `<diagram>` element
   - Or per large `<mxCell>` group
3. Store each chunk as a valid partial XML fragment
4. Record chunk ordering metadata

Agents MUST NOT:
- Split in the middle of XML tags
- Break ID references across chunks without tracking

---

### Chunk Editing Workflow

1. Load and validate each chunk independently
2. Apply modifications only to relevant chunks
3. Preserve all untouched chunks verbatim
4. Reassemble chunks in original order
5. Validate full XML integrity
6. Replace original file only after validation

Temporary chunks MUST be deleted after success unless debugging is required.

---

## Creating Large draw.io Files

When generating large diagrams:

- Build diagrams incrementally
- Generate separate logical diagram sections first
- Assemble into a final `.draw.io` file
- Validate after each assembly step

Agents MUST:
- Avoid generating thousands of nodes in one pass
- Prefer modular diagrams when possible

---

## Validation Rules

After creation or modification:

- Validate XML structure
- Confirm:
  - All referenced IDs exist
  - No duplicate IDs
  - All diagrams loadable by draw.io
- Ensure file remains text-based and readable

If validation fails:
- Abort replacement
- Restore from backup
- Log error details

---

## Temporary File Rules

- All intermediate files MUST be stored in:
  - `/tmp/windsurf/<operation-id>/`
- Never write intermediate XML next to the original
- Clean up temporary files after success

---

## Error Handling

- Any XML parsing error is a hard failure
- Never attempt auto-repair unless explicitly instructed
- Do not guess missing structures

Agents MUST log:
- Operation type
- Chunk count
- Validation results
- Failure reasons

---

## Security and Safety

- Do not execute embedded scripts
- Do not load external resources
- Do not follow external links
- Sanitize file paths

---

## Summary Principle

draw.io files are **structured diagrams, not documents**.

Treat them as:
- Structured XML
- Fragile
- Order-dependent
- ID-sensitive

All operations must be:
- Reversible
- Chunk-safe
- Strictly validated
- Deterministic

---

---

## CLI Export: Converting .drawio Files to PNG / PDF

A **.drawio file** (from draw.io / diagrams.net) can be converted to PNG or PDF via CLI. The `.drawio` extension is sometimes mistyped as `.draw.iko`, but it is the same format (XML or compressed XML).

### Recommended CLI tool

Use the official CLI provided by diagrams.net.

---

### Option 1. Using the diagrams.net CLI

#### Install (Linux)

```bash
sudo apt install drawio
```

Or download the AppImage from diagrams.net.

---

#### Convert to PNG

```bash
drawio --export --format png --output output.png input.drawio
```

---

#### Convert to PDF

```bash
drawio --export --format pdf --output output.pdf input.drawio
```

---

#### Useful flags

```bash
--scale 2              # higher resolution
--transparent         # PNG transparency
--page-index 0        # export specific page
--crop                # remove whitespace
```

---

### Option 2. Headless export (no GUI)

If you're running on a server:

```bash
drawio --export --format pdf --no-sandbox input.drawio
```

---

### Option 3. Docker (clean CI setup)

```bash
docker run --rm -v $PWD:/data rlespinasse/drawio \
  --export --format png --output /data/output.png /data/input.drawio
```

---

### Important caveats

- `.drawio` files are **XML**, sometimes compressed. No conversion without the draw.io engine
- Direct conversion via ImageMagick, etc., **won't work**
- If your file is actually `.draw.iko`, verify:

  ```bash
  file input.draw.iko
  ```

  It should report XML or compressed data

---

### Bottom line

- Fully supported via CLI
- Use `drawio --export`
- Works well in scripts, CI pipelines, and headless environments

---

## Citation Format — Never Cite by Catalogue Row Number (mandatory, all diagrams)

Node labels, annotations, and cited-work callouts on any `.drawio` diagram must never reference a literature-catalogue row number (e.g. "S#123", "[S123]", "S No 123"). The catalogue's `S No` column is an internal, mutable row index that gets renumbered and deduplicated over time, so a diagram annotation anchored to it silently points at the wrong source later. Annotate diagram nodes with `<short title>, <author> et al., <year>` (DOI/arXiv ID optional, add where space allows) instead.
