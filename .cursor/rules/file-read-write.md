---
trigger: always_on
---

# File Reading and Writing Guidelines

These rules define safe, scalable, and failure-resistant practices for handling files, especially large or critical ones.

The primary goals are:
- Prevent memory exhaustion
- Avoid data loss or corruption
- Enable recovery from partial failures
- Ensure predictable and verifiable behavior

---

## File Reading

### Pre-read analysis
- Always obtain file metadata before reading:
  - File size in bytes
  - Estimated line count when feasible
  - Encoding
  - Permissions and ownership
  - Last modified timestamp
- Refuse to load entire files into memory when size exceeds safe thresholds.
- Log metadata before processing.

### Chunked reading
- Break large files into manageable chunks when operating in code mode.
- Use fixed chunk sizes based on:
  - Line count (for text files)
  - Byte size (for binary files)
- Process chunks sequentially.
- Never assume the file fits in memory.
- Always delete temporary chunk files after successful processing.
- If processing fails, keep chunks only if required for debugging.

### Streaming and buffering
- Use buffered readers for all file input.
- Prefer streaming APIs over loading full file contents.
- Explicitly define buffer sizes when working with large files.

### Resource safety
- Always use try-with-resources for file streams and readers.
- Always implement try-catch-finally blocks:
  - `try`: main file operations
  - `catch`: log and classify errors
  - `finally`: close resources and clean temporary files

### Validation
- Validate encoding before parsing.
- Detect and handle:
  - Truncated files
  - Corrupted lines
  - Unexpected binary data
- Fail fast on invalid structure when appropriate.

---

## File Writing

### Pre-write analysis
- Obtain metadata of the target file or destination directory:
  - Existing file size
  - Available disk space
  - Permissions
  - Filesystem type
- Estimate output size before writing.
- Abort if insufficient disk space is detected.

### Chunked writing
- Write data in small, deterministic chunks.
- Append chunks sequentially to the destination file.
- Flush buffers after each chunk for critical files.
- Never write large files in a single memory operation.

### Backups and versioning
- Before modifying any existing file:
  - Create a full backup copy
  - Preserve timestamps and permissions when possible
- Do not delete backups unless explicitly instructed.

**Note:** In some cases like csv's or txt's, where you just need to add info at end of document, you can use the relevant python or linux command to add the specific test at End of File.

### Safe modification workflow

Preferred approaches:

#### Option A: Chunk-edit-reassemble
1. Create backup of original file.
2. Split original file into ordered chunks:
   - Example: 100 lines per chunk
3. Modify only the required chunks.
4. Reassemble chunks into a new file.
5. Validate integrity.
6. Replace the original file.
7. Remove temporary chunks.
8. Keep backup unless explicitly told to delete it.

#### Option B: Versioned replacement
1. Write new file in chunks as `<filename>-v<version>.ext`
2. Validate file content and size.
3. Delete original file.
4. Rename new file to original filename.
5. Keep previous version as backup unless instructed otherwise.

### Streaming and buffering
- Always use buffered writers.
- Avoid holding full file contents in memory.
- Define buffer sizes explicitly for large outputs.

### Resource safety
- Use try-with-resources for writers and streams.
- Use try-catch-finally blocks:
  - Catch and log partial writes
  - Ensure file handles are closed
  - Clean temporary files on failure

### Atomicity and consistency
- Prefer atomic file replacement when supported by the filesystem.
- Avoid leaving partially written files with the final filename.
- Use temporary filenames during writes, then rename.

### Validation after writing
- Verify:
  - File size
  - Line count (if applicable)
  - Checksums for critical files
- Confirm encoding correctness.
- Confirm file permissions.

---

## Error Handling and Logging

- Log all file operations:
  - Read start and completion
  - Write start and completion
  - Chunk creation and deletion
  - Backup creation
  - Failures and exceptions
- Include:
  - File path
  - File size
  - Operation type
  - Timestamp
  - Error stack trace

---

## Security Considerations

- Never trust file paths from unvalidated input.
- Prevent directory traversal.
- Avoid following symbolic links unless explicitly required.
- Restrict write operations to approved directories.
- Sanitize filenames.

---

## Cleanup Rules

- Always delete:
  - Temporary chunk files
  - Temporary output files
  - Intermediate buffers stored on disk
- Never delete:
  - Backups
  - Versioned files
  unless explicitly instructed.

---

## Performance Guidelines

- Prefer sequential disk access.
- Avoid random seeking in large files.
- Use reasonable buffer sizes:
  - Typically 8 KB to 1 MB depending on context
- Parallelize chunk processing only when file ordering is not required.

---

## Summary Principle

Treat every file as:
- Potentially large
- Potentially fragile
- Potentially irreplaceable

Design every operation to be reversible, observable, and safe by default.

---

## Handling Non-Text and Restricted File Types

These rules define how to safely and deterministically extract readable content from file formats that are not directly accessible, not reliably parsable, or partially encrypted. The goal is to convert all supported formats into `.txt` or `.md` representations inside a temporary workspace before any analysis.

---

## General Principles

- Never attempt to parse proprietary or binary formats directly.
- Always convert to a plain text intermediary format.
- Perform all conversions inside a dedicated temporary directory.
- Treat extracted text as derived data, not as the original source of truth.
- Preserve the original file unchanged.
- Clean up temporary artifacts after successful processing.

---

## Temporary Workspace Rules

- Create a per-operation temporary directory, for example:
  - `/tmp/windsurf/<operation-id>/`
- Store all derived files inside this directory.
- Use deterministic filenames:
  - `<original-name>.txt`
  - `<original-name>.md`
- Delete the temporary directory after processing unless debugging is explicitly required.
- Never write converted output next to the original file.

---

## File Type Specific Handling

### PDF Files (`.pdf`)

Processing order:
1. Attempt text extraction using `pdftotext`.
2. Validate extracted text:
   - Non-empty
   - Reasonable character distribution
3. If text extraction fails or produces mostly unreadable output:
   - Render pages to images.
   - Apply OCR using `tesseract`.
4. Save final output as `.txt` or `.md` in temporary folder like `/tmp/windsurf/<operation-id>/`.

Rules:
- Detect encrypted or password-protected PDFs.
- If encrypted and password is unavailable, log and abort extraction.
- Record page count and extraction method used.

---

### Word Documents (`.docx`)

Processing order:
1. Convert using `pandoc` or equivalent.
2. Prefer conversion to Markdown.
3. Fall back to plain text if Markdown conversion fails.

Rules:
- Preserve heading structure when converting to Markdown.
- Ignore embedded media unless explicitly required.
- Validate encoding and line structure after conversion.
- Save final output as `.txt` or `.md` in temporary folder like `/tmp/windsurf/<operation-id>/`.

---

### PowerPoint Files (`.pptx`)

Processing order:
1. Extract slide text using `pandoc` or a structured extractor.
2. Convert to Markdown with slide separators.
3. If slides contain images with text:
   - Render slide images.
   - Apply OCR selectively.

Rules:
- Preserve slide order.
- Annotate slide boundaries clearly.
- Ignore animations and transitions.

---

### Excel and Spreadsheet Files (`.xlsx`, `.csv`)

Processing order:
1. Convert sheets to CSV or Markdown tables.
2. Process each sheet independently.
3. Concatenate results with clear sheet separators.

Rules:
- Never load entire spreadsheets into memory if large.
- Stream rows when possible.
- Detect and log formulas separately from computed values.

---

### Image Files (`.png`, `.jpg`, `.jpeg`, `.tiff`)

Processing order:
1. Apply OCR using `tesseract`.
2. Post-process text to normalize spacing and line breaks.
3. Save extracted text as `.txt` `.html` or `.md` in temporary folder like `/tmp/windsurf/<operation-id>/`.

Rules:
- Log image resolution and OCR language.
- If OCR confidence is low, annotate output as unreliable.

---

### Unsupported or Unknown File Types

- Do not attempt heuristic parsing.
- Log file type, size, and rejection reason.
- Abort processing unless explicit override is provided.

---

## Validation After Conversion

- Verify output file exists and is non-empty.
- Confirm encoding is UTF-8.
- Log:
  - Original file type
  - Conversion tool used
  - Output size
  - Success or failure state

---

## Security and Safety Constraints

- Never execute macros or embedded scripts.
- Disable external resource loading during conversion.
- Do not follow links embedded in documents.
- Sanitize all filenames used in temporary paths.

---

## Summary Rule

All non-plain-text files must be transformed into a readable `.txt` or `.md` representation in a temporary workspace before analysis. Direct inspection of proprietary or binary formats is forbidden.

---

---

## Mandatory Tool Execution and Fallback Rules

These rules define deterministic behavior when file conversion or text extraction tools fail.

Agents MUST follow the fallback sequence exactly as defined. Skipping steps is forbidden unless explicitly stated.

---

## Failure Detection Criteria

A tool execution is considered failed if ANY of the following occur:
- Non-zero exit code
- Output file is missing
- Output file size is below a minimal threshold (configurable, default 1 KB)
- Output contains predominantly non-printable or replacement characters
- Explicit error messages are detected in stderr

Failures MUST be logged with tool name, command, and error output.

---

## PDF Extraction Fallback Chain

1. **Primary**
   - Run `pdftotext`
2. **Secondary**
   - Render pages to images
   - Run `tesseract` OCR
3. **Tertiary**
   - Use a Python PDF parsing library (e.g. `pdfminer.six`)
4. **Abort**
   - Mark extraction as failed
   - Do not attempt further processing

Each step MUST only proceed if the previous step failed.

---

## Image OCR Fallback Chain

1. **Primary**
   - Run `tesseract`
2. **Secondary**
   - Preprocess images (grayscale, thresholding)
   - Retry `tesseract`
3. **Tertiary**
   - Use an alternative OCR engine or library if available
4. **Abort**
   - Mark OCR as unreliable or failed

---

## DOCX / PPTX Conversion Fallback Chain

1. **Primary**
   - Convert using `pandoc`
2. **Secondary**
   - Use a Python-based parser (`python-docx`, `python-pptx`)
3. **Abort**
   - Mark conversion as failed

---

## Mandatory Execution Requirements

- Agents MUST attempt execution of CLI tools when available.
- If CLI tools are unavailable, agents MUST attempt equivalent Python libraries.
- Agents MUST NOT silently skip a conversion step.
- Each fallback attempt MUST be logged.

---

## Termination Rules

- After exhausting all fallback options, agents MUST:
  - Stop further attempts
  - Preserve logs
  - Mark content as unavailable or unreliable
- Agents MUST NOT hallucinate content.

---

## Summary Principle

Tool failure is expected. Silent failure is forbidden.

Every extraction attempt must either:
- Produce validated text
- Or terminate with an explicit, logged failure state.

---

## Citation Format — Never Cite by Catalogue Row Number (mandatory, all documents)

Never cite a source by its literature-catalogue row identifier (e.g. "S#123", "[S123]", "S No 123", "catalogue row 123") in any document this project produces — papers, survey/thesis skeletons, technical reports, changelog or session notes, architecture-diagram node labels/annotations, or anywhere else. The catalogue CSV's "S No" column is an internal, mutable row index: it gets renumbered and deduplicated over time, so a citation anchored to it silently points at the wrong source later. It is not a citation.

Always cite as: `<short title>, <author> et al., <year>`, with the DOI or arXiv ID appended where available (e.g. "GraphRAG, Edge et al., 2024, arXiv:2404.16130"). If a source is cited more than once in the same document, number it (`[1]`, `\cite{key}`, etc.) backed by a proper bibliography/reference list at the end of the document — never as a bare catalogue-row pointer in the running text.
