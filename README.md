# Code-Parser-Analyzer-AutoGen-GEMINI
Code Parser &amp; Analyzer using Microsoft AutoGen &amp; Gemini API Key
# Code Parser & Analyzer

Gemini-powered autogen framework that converts raw code into structured intermediate representation (IR) with AST, symbol tables, and control/data flow graphs.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set Gemini API key in `.env` file (already configured)

## Usage

```bash
python main.py
```

1. Enter your code (press Enter twice to finish)
2. Specify programming language (default: python)
3. Get JSON output saved to `code_analysis_ir.json`

## Output Format

```json
{
  "language": "python",
  "ast": {
    "type": "Module",
    "children": [...]
  },
  "symbols": [
    {"name": "variable", "type": "int", "scope": "global"}
  ],
  "control_flow": [
    {"source": "node1", "target": "node2"}
  ],
  "data_flow": [
    {"variable": "x", "from": "assign", "to": "use"}
  ]
}
```

## Agents

- **AST_Parser**: Generates abstract syntax tree
- **Symbol_Analyzer**: Extracts variables and functions
- **Flow_Analyzer**: Analyzes execution flow and dependencies

## Files

- `main.py` - Main framework
- `requirements.txt` - Dependencies
- `.env` - API key configuration
- `sample.txt` - sample codes 
