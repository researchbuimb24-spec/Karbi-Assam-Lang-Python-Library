# Contributing to the Karbi Language Library (`karbi`)

Thank you for your interest in contributing to the **Karbi Language Library**!

Karbi (*Arleng Alam*) is a Sino-Tibetan / Tibeto-Burman language spoken primarily in Karbi Anglong and West Karbi Anglong districts of Assam, Meghalaya, and adjacent areas of Northeast India.

Because this library documents indigenous linguistic and cultural heritage, we maintain strict standards regarding **linguistic accuracy, bibliographic provenance, and cultural ethics**.

---

## Table of Contents
1. [Core Principles & Cultural Ethics](#core-principles--cultural-ethics)
2. [Dataset Architecture](#dataset-architecture)
3. [Step-by-Step Contribution Workflow](#step-by-step-contribution-workflow)
   - [Step 1: Register Your Source](#step-1-register-your-source)
   - [Step 2: Add or Update Lexical Entries](#step-2-add-or-update-lexical-entries)
   - [Step 3: Verification Rules & AI Candidates](#step-3-verification-rules--ai-candidates)
   - [Step 4: Validate Your Changes](#step-4-validate-your-changes)
4. [Schema Reference & Templates](#schema-reference--templates)
   - [Source Schema (`sources.jsonl`)](#source-schema)
   - [Lexicon Schema (`core_lexicon.jsonl`)](#lexicon-schema)
5. [Validation CLI & Python API](#validation-cli--python-api)
6. [Pre-Submission Checklist](#pre-submission-checklist)

---

## Core Principles & Cultural Ethics

To ensure the library remains a reliable, trusted linguistic resource:

1. **No Invented Words or Translations**: Never generate, hallucinate, or synthesize Karbi words, affixes, or translations. Every entry must be derived from an attested bibliographic publication, oral recording, or verified native-speaker consultation.
2. **Explicit Verification Tracking**: Translations or glosses that have not completed authorized native-speaker review must remain marked `verified: false`.
3. **Fail-Closed Verification Engine**: The validation system rejects any entry claiming `VERIFIED` status without documented evidence reviewed by authorized reviewers.
4. **No Silent Modifiers**: The validation tool (`karbi validate`) strictly audits data without altering or overwriting your files.
5. **Respect for Cultural Knowledge**: Sacred rituals, deities, and traditional clan practices must adhere to the community ethics policy (`karbi.culture.get_cultural_ethics_policy()`).

---

## Dataset Architecture

The repository separates authoritative development data from packaged distribution resources:

```
Arunachal-Pradesh-Lang-Python-Library/
├── data/                               # Authoritative development datasets
│   ├── lexicon/
│   │   └── core_lexicon.jsonl          # Authoritative Karbi lexicon records
│   └── sources/
│       └── sources.jsonl               # Authoritative bibliographic source registry
├── src/karbi/resources/                # Synchronized distribution resources
│   ├── lexicon/core_lexicon.jsonl
│   └── sources/sources.jsonl
└── tests/                              # Pytest test suite
```

> **Important**: Always edit the authoritative files in the `data/` directory. When building or running locally, the library automatically synchronizes `data/` to `src/karbi/resources/`.

Both datasets use **JSON Lines (`.jsonl`) format**, where **each line must be a single, valid JSON object** followed by a newline.

---

## Step-by-Step Contribution Workflow

### Step 1: Register Your Source

Before adding a lexical entry, ensure its source is registered in `data/sources/sources.jsonl`. If you are citing a publication or dictionary not yet registered, append a new line to `data/sources/sources.jsonl`.

Example source entry:
```json
{"source_id": "SRC-PUB-1925-GRND", "source_type": "print_publication", "title": "An English-Mikir Vocabulary", "creators": [{"name": "Sardoka Perrin Kay", "role": "author"}, {"name": "Edward Stack", "role": "contributor"}], "publication_details": {"publisher": "Assam Secretariat Press", "place": "Shillong", "year": 1925}, "archive_location": "National Library of India", "rights_and_permissions": {"status": "public_domain", "license": "Public Domain", "access_restrictions": "none"}}
```

- **`source_id` Format**: Use uppercase alphanumeric codes with hyphens, e.g., `SRC-PUB-<YEAR>-<SHORTNAME>` or `SRC-ORAL-<YEAR>-<COLLECTION>`.
- Must be unique across all source files.

### Step 2: Add or Update Lexical Entries

Add your entry to `data/lexicon/core_lexicon.jsonl` as a single JSON line.

Example entry:
```json
{"id": "KB-LEX-0000031", "headword": {"lemma": "arhe", "script": "latin", "phonetics": {"ipa": "/aɾ.he/"}, "contemporary_spelling_variants": []}, "dialect": {"primary_variety": "rongkhang", "notes": ""}, "morphology": {"pos": "noun", "is_compound": false}, "senses": [{"sense_id": "S1", "part_of_speech": "noun", "definitions": {"en": [{"text": "price, cost, value", "verified": true}], "hi": [{"text": "मूल्य, कीमत", "verified": false}], "as": [{"text": "মূল্য, দাম", "verified": false}], "bn": [{"text": "মূল্য, দাম", "verified": false}]}, "gloss_provenance": {"en": "bibliographic", "hi": "unverified", "as": "unverified", "bn": "unverified"}, "evidence": [{"source_id": "SRC-PUB-1925-GRND", "locator": "p. 112", "context": "arhe ke-un (affordable)"}], "status": "SOURCE_ATTESTED", "cultural_notes": "", "allow_indexing": true}], "status": "SOURCE_ATTESTED", "verification_history": [{"action": "ingest", "timestamp": "2026-10-17T00:00:00Z", "performed_by": "contributor_username", "notes": "Attested in 1925 English-Mikir Vocabulary"}], "cross_references": []}
```

Key fields to check:
1. **`id`**: Must match `^KB-LEX-[0-9]{7}$` (e.g. `KB-LEX-0000031`) and be unique across the entire lexicon.
2. **`headword.lemma`**: Standardized Roman/Latin Karbi orthography in lowercase.
3. **`senses[].evidence`**: Every sense must cite at least one registered `source_id` matching an entry in `sources.jsonl`, along with a specific page or locator.
4. **`cross_references`**: Any linked `target_entry_id` must already exist in the lexicon.

### Step 3: Verification Rules & AI Candidates

#### Verification Lifecycle Statuses:
- **`DRAFT`**: Work-in-progress entry.
- **`COMMUNITY_SUBMITTED`**: Contributed by community members or language learners, pending native speaker or scholar review.
- **`AI_CANDIDATE`**: Model-suggested translations or lexical analyses. Must remain unverified until approved.
- **`SOURCE_ATTESTED`**: Backed by a verified bibliographic or archival source citation with locator.
- **`VERIFIED`**: Validated by registered authorized reviewers under formal review pathways.

#### Unverified Glosses Rule:
If an entry has Indic glosses (`hi`, `as`, `bn`) translated from English or suggested by AI that have not been vetted by a qualified bilingual speaker:
- Mark each definition item: `{"text": "...", "verified": false}`.
- Record provenance: `"gloss_provenance": {"hi": "unverified", "as": "unverified", "bn": "unverified"}`.
- Do **not** mark Indic glosses as `verified: true` based solely on automated translations.

### Step 4: Validate Your Changes

Run the validation CLI command:

```bash
karbi validate
```

If any errors, broken cross-references, or unreferenced sources are detected, fix them and re-run.

---

## Schema Reference & Templates

### Source Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `source_id` | `str` | Yes | Unique identifier (e.g. `SRC-PUB-1925-GRND`) |
| `source_type` | `str` | Yes | `print_publication`, `oral_recording`, `manuscript`, or `native_speaker_consultation` |
| `title` | `str` | Yes | Title of the publication or archive recording |
| `creators` | `list[dict]` | Yes | List of `{"name": "...", "role": "author|editor|consultant"}` |
| `publication_details` | `dict` | No | `{"publisher": "...", "place": "...", "year": 1925}` |
| `archive_location` | `str` | No | Physical or digital archive location |
| `rights_and_permissions` | `dict` | Yes | `{"status": "public_domain|copyrighted|open_access", "license": "..."}` |

### Lexicon Schema

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `str` | Yes | Format `KB-LEX-0000001` (7 digits) |
| `headword.lemma` | `str` | Yes | Canonical Karbi lemma |
| `headword.script` | `str` | Yes | Usually `"latin"` |
| `headword.phonetics.ipa` | `str` | No | IPA pronunciation (e.g. `"/aɾ.he/"`) |
| `headword.contemporary_spelling_variants` | `list[str]` | No | Alternative accepted spellings |
| `dialect.primary_variety` | `str` | Yes | E.g. `"rongkhang"`, `"amri"`, `"chinthong"` |
| `morphology.pos` | `str` | Yes | Part of speech (`noun`, `verb`, `adjective`, etc.) |
| `senses` | `list[dict]` | Yes | One or more semantic senses |
| `senses[].sense_id` | `str` | Yes | `S1`, `S2`, etc. |
| `senses[].part_of_speech` | `str` | Yes | Grammatical category of this sense |
| `senses[].definitions` | `dict[str, list]` | Yes | Glosses keyed by `en`, `hi`, `as`, `bn` |
| `senses[].evidence` | `list[dict]` | Yes | Citations with `source_id` and `locator` |
| `status` | `str` | Yes | `DRAFT`, `COMMUNITY_SUBMITTED`, `AI_CANDIDATE`, `SOURCE_ATTESTED`, or `VERIFIED` |
| `verification_history` | `list[dict]` | Yes | Provenance log of actions and timestamps |
| `cross_references` | `list[dict]` | No | Relations to existing entry IDs |

---

## Validation CLI & Python API

### CLI Usage

```bash
# Standard repository validation:
karbi validate

# Verbose output (lists all scanned files and audit breakdown):
karbi validate --verbose

# Strict mode (fails if unverified glosses are present):
karbi validate --strict

# Machine-readable JSON output (ideal for CI/CD workflows):
karbi validate --json

# Validate custom or staged files:
karbi validate --lexicon path/to/my_lexicon.jsonl --sources path/to/my_sources.jsonl
```

### Python API Usage

```python
import karbi

# Run validator on default or custom files
result = karbi.validate_dataset()

if not result.is_valid:
    print(f"Validation failed with {len(result.errors)} errors:")
    for err in result.errors:
        print(f"  - {err}")
else:
    print(f"Dataset is valid! {result.lexicon_entries_count} entries verified.")
    print(result.report(verbose=True))
```

---

## Pre-Submission Checklist

Before submitting a Pull Request, verify:

- [ ] All new sources are registered in `data/sources/sources.jsonl`.
- [ ] Every entry ID matches `KB-LEX-[0-9]{7}` and is strictly unique.
- [ ] Every sense contains a valid `source_id` present in `sources.jsonl` with page/locator.
- [ ] Any cross-reference points to a valid, existing entry ID.
- [ ] No unverified translation is claimed as `verified: true`.
- [ ] AI-generated suggestions are designated with `status: "AI_CANDIDATE"`.
- [ ] `karbi validate` reports zero errors.
- [ ] All tests pass: `pytest`.
