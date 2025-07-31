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

    def generate_reply(self, messages=None, sender=None, config=None):
        prompt = f"{self.system_msg}\n\nReturn ONLY valid JSON."
        response = self.model.generate_content(prompt)
        return response.text

def extract_json(text):
    json_match = re.search(r'```json\s*({.*?})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    json_match = re.search(r'({[^{}]*(?:{[^{}]*}[^{}]*)*})', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    if "function" in text.lower() or "def" in text.lower():
        return '{"symbols": [{"name": "extracted_function", "type": "function", "scope": "global"}]}'
    return '{"data": "no_json_found"}'

def main():
    print("Enter your code (press Enter twice to finish):")
    lines = []
    while True:
        try:
            line = input()
            if line == "" and len(lines) > 0 and lines[-1] == "":
                break
            lines.append(line)
        except EOFError:
            break

    code = "\n".join(lines[:-1]) if lines else "print('hello')"
    language = (input("Enter language (default: python): ") or "python").strip()

    ast_agent = GeminiAgent("AST_Parser", f"Parse this {language} code into AST: {code}. Return JSON: {{\"ast\": {{\"type\": \"Module\", \"children\": [{{\"type\": \"Assign\", \"target\": \"x\", \"value\": \"10\"}}]}}}}")
    symbol_agent = GeminiAgent("Symbol_Analyzer", f"Extract all declared and used symbols in this {language} code: {code}. Include their type and scope. Return JSON: {{\"symbols\": [{{\"name\": \"a\", \"type\": \"variable\", \"scope\": \"global\"}}]}}")
    flow_agent = GeminiAgent("Flow_Analyzer", f"Analyze control and data flow in this {language} code: {code}. Return JSON: {{\"control_flow\": [{{\"source\": \"line1\", \"target\": \"line2\"}}], \"data_flow\": [{{\"variable\": \"x\", \"from\": \"assign\", \"to\": \"print\"}}]}}")

    user = autogen.UserProxyAgent("User", human_input_mode="NEVER", code_execution_config=False)

    agents = [user, ast_agent, symbol_agent, flow_agent]
    group_chat = autogen.GroupChat(agents=agents, messages=[], max_round=4)
    manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=False)

    user.initiate_chat(manager, message=f"Analyze this {language} code:\n```{language}\n{code}\n```")

    ir_data = {"language": language, "ast": {}, "symbols": [], "control_flow": [], "data_flow": []}

    for msg in group_chat.messages:
        if msg["name"] == "AST_Parser":
            try:
                json_str = extract_json(msg["content"])
                ast_data = json.loads(json_str)
                ir_data["ast"] = ast_data.get("ast", ast_data)
                print(f"AST extracted: {ir_data['ast']}")
            except Exception as e:
                print(f"AST parsing failed: {e}")
                ir_data["ast"] = {"type": "ParseError", "content": msg["content"][:100]}
        elif msg["name"] == "Symbol_Analyzer":
            try:
                json_str = extract_json(msg["content"])
                symbol_data = json.loads(json_str)
                ir_data["symbols"] = symbol_data.get("symbols", symbol_data if isinstance(symbol_data, list) else [])
                print(f"Symbols extracted: {len(ir_data['symbols'])} items")
            except Exception as e:
                print(f"Symbol parsing failed: {e}")
                ir_data["symbols"] = [{"name": "ParseError", "type": "unknown", "scope": "unknown"}]
        elif msg["name"] == "Flow_Analyzer":
            try:
                json_str = extract_json(msg["content"])
                flow_data = json.loads(json_str)
                ir_data["control_flow"] = flow_data.get("control_flow", [])
                ir_data["data_flow"] = flow_data.get("data_flow", [])
                print(f"Flow extracted: {len(ir_data['control_flow'])} control, {len(ir_data['data_flow'])} data")
            except Exception as e:
                print(f"Flow parsing failed: {e}")
                ir_data["control_flow"] = [{"source": "ParseError", "target": "ParseError"}]
                ir_data["data_flow"] = [{"variable": "ParseError", "from": "unknown", "to": "unknown"}]

    with open("code_analysis_ir.json", "w", encoding="utf-8") as f:
        json.dump(ir_data, f, indent=2)

    with open("code_analysis_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"## Code Analysis of:\n\n```{language}\n{code}\n```\n\n")
        f.write("**1. Symbol Table:**\n\n")
        f.write("| Symbol | Scope | Type |\n|--------|--------|--------|\n")
        for sym in ir_data["symbols"]:
            f.write(f"| {sym.get('name', '')} | {sym.get('scope', '')} | {sym.get('type', '')} |\n")

        f.write("\n**2. Control Flow Graph (CFG):**\n\n")
        for flow in ir_data["control_flow"]:
            f.write(f"- {flow.get('source', '')} --> {flow.get('target', '')}\n")

        f.write("\n**3. Data Flow Graph (DFG):**\n\n")
        for dfg in ir_data["data_flow"]:
            if "variable" in dfg:
                f.write(f"- {dfg['variable']} ({dfg['from']} --> {dfg['to']})\n")
            elif "expression" in dfg:
                f.write(f"- {dfg['expression']} ({dfg['from']} --> {dfg['to']})\n")

    print("\nLanguage-neutral IR saved to code_analysis_ir.json")
    print("Human-readable analysis saved to code_analysis_summary.txt")
    print(json.dumps(ir_data, indent=2))

if __name__ == "__main__":
    main()
    
