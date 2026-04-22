# BRD Template Upload Guide

Quick reference for uploading custom BRD templates to the system.

## Quick Start

### Method 1: Extract from Existing Documents (Easiest)

```bash
# Navigate to template extraction tool
cd src/agents/brd_generator/utils

# Extract from DOCX
python template_extractor.py "C:\path\to\template.docx" "my_template" "Description"

# Extract from PDF
python template_extractor.py "C:\path\to\template.pdf" "my_template" "Description"

# Extract from TXT
python template_extractor.py "template.txt" "my_template" "Description"
```

✅ **Template is immediately available** - no restart needed!

### Method 2: Create JSON Manually

Create a file in `src/agents/brd_generator/templates/my_template.json`:

```json
{
  "template_id": "my_template",
  "template_name": "My Custom Template",
  "description": "Custom template for specific use case",
  "use_case": "Internal projects",
  "sections": [
    {
      "section_id": "overview",
      "title": "Project Overview",
      "required": true,
      "description": "High-level summary",
      "subsections": ["Background", "Objectives"]
    }
  ],
  "formatting": {
    "style": "professional",
    "tone": "business-professional"
  }
}
```

## Using Your Template

```bash
# Explicit selection
python supervisor.py "Build dashboard" --template my_template

# Auto-selection (add keywords to template_config.json)
python supervisor.py "Build internal dashboard"
```

## Add Auto-Selection Rules

Edit `src/agents/brd_generator/templates/template_config.json`:

```json
{
  "template_selection_rules": {
    "rules": [
      {
        "keywords": ["internal", "dashboard"],
        "template": "my_template",
        "priority": 8
      }
    ]
  }
}
```

## Verify Template Loaded

```python
from src.agents.brd_generator.utils.template_manager import SimpleBRDTemplateManager

manager = SimpleBRDTemplateManager()
templates = manager.get_available_templates()

for t in templates:
    print(f"✓ {t['template_id']}: {t['template_name']}")
```

## Template JSON Structure

### Required Fields
- `template_id` - Unique identifier (lowercase, underscores)
- `template_name` - Display name
- `description` - Template purpose
- `sections` - Array of section objects

### Section Object
- `section_id` - Unique identifier
- `title` - Section heading
- `required` - Boolean (true/false)
- `description` - Section purpose
- `subsections` - Array of subsection titles (optional)

### Optional Fields
- `use_case` - When to use this template
- `formatting` - Style preferences
  - `style`: formal | professional | casual
  - `tone`: executive | technical | entrepreneurial
  - `length`: brief | comprehensive | detailed
  - `include_diagrams`: true | false
  - `include_tables`: true | false

## Built-in Templates

| Template ID | Sections | Use Case |
|------------|----------|----------|
| `standard_brd` | 9 | General-purpose (default) |
| `enterprise_brd` | 13 | Government, compliance, enterprise |
| `lean_brd` | 8 | Startups, MVPs, rapid prototyping |

## Troubleshooting

**Template not showing up?**
- Check JSON syntax (use validator: jsonlint.com)
- Verify file is in `src/agents/brd_generator/templates/`
- Ensure `template_id` matches filename (without .json)

**Template not auto-selecting?**
- Check keywords in `template_config.json`
- Higher priority wins (use 8-11 for highest priority)
- Test with: `manager.auto_select_template("your prompt here")`

**Extraction failed?**
- Supported formats: DOCX, PDF, TXT only
- Check file exists and is readable
- Verify document has clear section headings

## Examples

**Corporate Template:**
```bash
python template_extractor.py "CorporateStandard.docx" "corporate_brd" "Standard corporate BRD format"
python supervisor.py "Build CRM system" --template corporate_brd
```

**Startup Template:**
```bash
python template_extractor.py "LeanCanvas.pdf" "startup_lean" "Lean canvas for startups"
python supervisor.py "MVP for delivery app" --template startup_lean
```

## More Information

See [README.md](README.md#-brd-templates) for comprehensive template documentation.
