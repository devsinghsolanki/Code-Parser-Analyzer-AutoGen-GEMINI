import os
import json
import re
import autogen
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiAgent(autogen.ConversableAgent):
    def __init__(self, name, system_message):
        super().__init__(name=name, llm_config=False, human_input_mode="NEVER")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.system_msg = system_message

    def generate_reply(self, code):
        prompt = (
            self.system_msg +
            "\n\nReturn ONLY valid JSON wrapped in triple backticks labeled as json.\n\n" +
            "Code:\n" + code
        )
        response = self.model.generate_content(prompt)
        return response.text

def extract_json(text):
    # Fix: correctly capture JSON inside ```json ... ```
    triple_backtick_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if triple_backtick_match:
        return triple_backtick_match.group(1)

    # Fallback: extract first balanced JSON object
    brace_pos = text.find('{')
    if brace_pos == -1:
        return None

    stack = []
    start = -1
    for i in range(brace_pos, len(text)):
        c = text[i]
        if c == '{':
            if start == -1:
                start = i
            stack.append(c)
        elif c == '}':
            if stack:
                stack.pop()
                if len(stack) == 0:
                    return text[start:i+1]
    return None

def main():
    print("Enter your code (finish input with an empty line):")
    lines = []
    while True:
        try:
            line = input()
            if line == "" and (len(lines) == 0 or lines[-1] == ""):
                break
            lines.append(line)
        except EOFError:
            break

    code = "\n".join(lines).strip()
    if not code:
        print("No code entered, exiting.")
        return

    language = input("Enter programming language (default: python): ").strip() or "python"

    ast_prompt = (
        f"Parse this {language} code to generate a detailed Abstract Syntax Tree (AST). "
        "Return the AST as valid JSON enclosed in triple backticks labeled json."
    )
    symbol_prompt = (
        f"Extract declared and used symbols in this {language} code. For each symbol, provide its name, type, and scope. "
        "Return the data as valid JSON enclosed in triple backticks labeled json."
    )
    flow_prompt = (
        f"Perform control and data flow analysis on this {language} code. "
        "Return JSON with two top-level keys: 'control_flow' (list of objects with source,target) "
        "and 'data_flow' (list of objects with variable, from, to). "
        "Wrap the JSON in triple backticks labeled json."
    )

    ast_agent = GeminiAgent("AST_Parser", ast_prompt)
    symbol_agent = GeminiAgent("Symbol_Analyzer", symbol_prompt)
    flow_agent = GeminiAgent("Flow_Analyzer", flow_prompt)

    ast_resp = ast_agent.generate_reply(code)
    symbol_resp = symbol_agent.generate_reply(code)
    flow_resp = flow_agent.generate_reply(code)

    try:
        ast_json_str = extract_json(ast_resp)
        ast_json = json.loads(ast_json_str) if ast_json_str else {}
    except Exception as e:
        print(f"Error parsing AST JSON: {e}")
        ast_json = {}

    try:
        symbol_json_str = extract_json(symbol_resp)
        symbol_json = json.loads(symbol_json_str) if symbol_json_str else []
    except Exception as e:
        print(f"Error parsing Symbol JSON: {e}")
        symbol_json = []

    try:
        flow_json_str = extract_json(flow_resp)
        flow_json = json.loads(flow_json_str) if flow_json_str else {}
    except Exception as e:
        print(f"Error parsing Flow JSON: {e}")
        flow_json = {}

    symbols_processed = symbol_json if isinstance(symbol_json, list) else symbol_json.get("symbols", [])

    ir_data = {
        "language": language,
        "ast": ast_json.get("ast", ast_json),
        "symbols": symbols_processed,
        "control_flow": flow_json.get("control_flow", []),
        "data_flow": flow_json.get("data_flow", [])
    }

    with open("code_analysis_ir.json", "w", encoding="utf-8") as f_json:
        json.dump(ir_data, f_json, indent=2)

    with open("code_analysis_summary.txt", "w", encoding="utf-8") as f_summary:
        f_summary.write(f"## Code Analysis of:\n\n``````\n\n")

        f_summary.write("**1. Symbol Table:**\n\n")
        f_summary.write("| Symbol | Scope | Type |\n|--------|-------|------|\n")
        if not ir_data["symbols"]:
            f_summary.write("| (none found) | | |\n")
        else:
            for sym in ir_data["symbols"]:
                f_summary.write(f"| {sym.get('name','')} | {sym.get('scope','')} | {sym.get('type','')} |\n")

        f_summary.write("\n**2. Control Flow Graph (CFG):**\n\n")
        if not ir_data["control_flow"]:
            f_summary.write("No control flow edges found.\n")
        else:
            for cf in ir_data["control_flow"]:
                source = cf.get("source", "")
                target = cf.get("target", "")
                f_summary.write(f"- {source} --> {target}\n")

        f_summary.write("\n**3. Data Flow Graph (DFG):**\n\n")
        if not ir_data["data_flow"]:
            f_summary.write("No data flow relations found.\n")
        else:
            for dfg in ir_data["data_flow"]:
                var = dfg.get("variable", dfg.get("expression", "<unknown>"))
                frm = dfg.get("from", "")
                to = dfg.get("to", "")
                f_summary.write(f"- {var} ({frm} --> {to})\n")

        f_summary.write("\n**4. AST Summary:**\n\n")
        ast_summary = json.dumps(ir_data["ast"], indent=2) if ir_data["ast"] else "No AST data found."
        f_summary.write(ast_summary + "\n")

    print("\nAnalysis completed.")
    print("Saved JSON IR to 'code_analysis_ir.json'")
    print("Saved human-readable analysis to 'code_analysis_summary.txt'")

    print(json.dumps(ir_data, indent=2))


if __name__ == "__main__":
    main()
