#!/usr/bin/env python3
"""Pupil Code terminal agent with automatic Ollama model discovery."""
import json, os, subprocess, urllib.request, urllib.error
from pathlib import Path

def enable_ansi():
    """Enable ANSI colors in Windows PowerShell/Terminal when possible."""
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass
    # Also helps terminals that enable VT processing automatically.
    os.system("")

def clear_screen():
    """Start the Pupil AI chat on a clean terminal screen."""
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")


def type_text(text, delay=0.008, rainbow=False):
    """Print a reply with a smooth typewriter animation; optionally use rainbow colors."""
    import sys, time
    text = str(text)
    rainbow_colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]
    for i, char in enumerate(text):
        if rainbow and char not in "\r\n\t":
            # Color spaces too, so rainbow replies look continuous rather than dotted.
            sys.stdout.write(rainbow_colors[i % len(rainbow_colors)] + char + "\033[0m")
        else:
            sys.stdout.write(char)
        sys.stdout.flush()
        if char in ".!?":
            time.sleep(delay * 7)
        elif char in ",;:":
            time.sleep(delay * 3)
        else:
            time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

MODE_ORDER = ["low", "med", "high", "ultra", "pupil max"]
MODE_DETAILS = {
    "low": {"label": "LOW", "delay": 0.003, "max_tokens": 700, "rounds": 4,
            "instruction": "Keep answers very concise. Prefer the fastest, simplest correct solution. Explain only essential steps."},
    "med": {"label": "MEDIUM", "delay": 0.006, "max_tokens": 1400, "rounds": 6,
            "instruction": "Balance speed and detail. Give a clear answer with practical steps and moderate explanation."},
    "high": {"label": "HIGH", "delay": 0.008, "max_tokens": 2400, "rounds": 8,
            "instruction": "Think carefully through the task, inspect relevant files, check edge cases, and explain the solution clearly."},
    "ultra": {"label": "ULTRA", "delay": 0.009, "max_tokens": 3200, "rounds": 10,
            "instruction": "Use a thorough, methodical approach. Break complex tasks into steps, verify assumptions, consider edge cases, and provide a detailed result."},
    "pupil max": {"label": "PUPIL MAX", "delay": 0.008, "max_tokens": 4096, "rounds": 12,
            "instruction": "Use the most thorough problem-solving style available in this app: analyze requirements carefully, plan multi-step work, inspect and verify relevant files, consider alternatives and edge cases, use tools when helpful, and give a polished, complete answer. Do not claim hidden capabilities or results you do not have."},
}

def normalize_mode(value):
    value = value.strip().lower().replace("_", " ").replace("-", " ")
    aliases = {"medium": "med", "normal": "med", "max": "pupil max", "pupilmax": "pupil max"}
    value = aliases.get(value, value)
    return value if value in MODE_DETAILS else None

def show_mode_menu(current_mode):
    """Smooth, in-place animated effort picker for Windows Terminal."""
    import sys, time
    reset, bold, dim = "\033[0m", "\033[1m", "\033[2m"
    labels = ["low", "medium", "high", "xhigh", "max"]
    mode_for_level = {"low": "low", "medium": "med", "high": "high", "xhigh": "ultra", "max": "pupil max"}
    level_for_mode = {v: k for k, v in mode_for_level.items()}
    descriptions = {
        "low": "Fast and concise", "medium": "Balanced everyday help", "high": "Careful and detailed",
        "xhigh": "Deep multi-step work", "max": "PUPIL MAX · rainbow replies"
    }
    selected = labels.index(level_for_mode.get(current_mode, "medium"))
    phase = 0
    width = 64
    positions = [2, 14, 27, 41, 55]

    def rgb(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    def render(first=False):
        nonlocal phase
        # Clear only when opening. Subsequent frames redraw in place, avoiding flicker.
        if first:
            sys.stdout.write("\033[2J\033[H")
        else:
            sys.stdout.write("\033[H")
        sys.stdout.write("\n  " + bold + "P U P I L   A I" + reset + "  " + dim + "EFFORT CONTROL" + reset + "\n")
        sys.stdout.write("  Choose how much effort Pupil AI should spend.\n\n  ")
        for x in range(width):
            t = ((x + phase) % width) / max(1, width - 1)
            r = int(80 + 100 * t); g = int(28 + 10 * (1 - t)); bl = int(155 + 90 * (1 - t))
            focus = abs(x - int((selected + 0.5) * width / len(labels))) < 7
            if focus:
                r, g, bl = min(255, r + 30), min(255, g + 28), min(255, bl + 15)
            sys.stdout.write(rgb(r, g, bl) + "━" + reset)
        sys.stdout.write("\n\n  ")
        line = [" "] * 66
        for i, label in enumerate(labels):
            for j, ch in enumerate(label.upper()):
                if positions[i] + j < len(line): line[positions[i] + j] = ch
        sys.stdout.write("".join(line) + "\n  ")
        marker = [" "] * 66
        marker[positions[selected] + max(0, (len(labels[selected]) - 1) // 2)] = "▲"
        sys.stdout.write("".join(marker) + "\n\n  ")
        active = mode_for_level[labels[selected]]
        color = "\033[95m" if active == "pupil max" else "\033[96m"
        sys.stdout.write(color + bold + "● " + labels[selected].upper() + reset + "  " + descriptions[labels[selected]] + "\n")
        sys.stdout.write("\n  " + dim + "← / → move   Enter select   S session only   Esc cancel" + reset + "\n")
        sys.stdout.write("  " + dim + "Effort changes response style and work budget, not the model's inherent capability." + reset + "\n")
        # Reserve a final line every frame so the menu never jumps when MAX is selected.
        if active == "pupil max":
            colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]
            banner = "  ✦ P U P I L   M A X   ·   R A I N B O W   M O D E   ✦"
            sys.stdout.write("  " + "".join(colors[(i + phase // 2) % len(colors)] + ch for i, ch in enumerate(banner.strip()) if ch != " ") + reset + "\n")
        else:
            sys.stdout.write("\n")
        sys.stdout.flush()
        phase = (phase + 2) % width

    if os.name == "nt":
        try:
            import msvcrt
            render(first=True)
            while True:
                # Animate while idle; consume keys without blocking the animation.
                if msvcrt.kbhit():
                    key = msvcrt.getwch()
                    if key in ("\x00", "\xe0"):
                        arrow = msvcrt.getwch()
                        if arrow == "K": selected = max(0, selected - 1)
                        elif arrow == "M": selected = min(len(labels) - 1, selected + 1)
                        render()
                    elif key in ("\r", "\n", "s", "S"):
                        chosen = mode_for_level[labels[selected]]
                        sys.stdout.write("\033[2J\033[H")
                        print("\n  " + ("\033[95m" if chosen == "pupil max" else "\033[96m") + bold + "✓ EFFORT SET: " + labels[selected].upper() + reset)
                        if key.lower() == "s": print("  Applied for this session only.")
                        if chosen == "pupil max": rainbow_line("✦ P U P I L   M A X   A C T I V A T E D ✦")
                        time.sleep(0.25)
                        return chosen
                    elif key == "\x1b" or key.lower() == "q":
                        sys.stdout.write("\033[2J\033[H")
                        return current_mode
                else:
                    render()
                    time.sleep(0.075)
        except (ImportError, OSError):
            pass

    # Portable fallback for terminals without native key input.
    render(first=True)
    answer = input("\n  Choose 1-5 or type a mode name (Enter keeps current): ").strip()
    if not answer: return current_mode
    if answer.lower() == "s": return mode_for_level[labels[selected]]
    if answer.isdigit() and 1 <= int(answer) <= len(labels): return mode_for_level[labels[int(answer)-1]]
    mode = normalize_mode(answer)
    if mode: return mode
    print("  Unknown mode. Keeping " + current_mode.upper() + ".")
    return current_mode

def rainbow_line(text):
    colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]
    reset = "\033[0m"
    print("  " + "".join((colors[i % len(colors)] + ch + reset) if ch != " " else ch for i, ch in enumerate(text)))

def show_chat_header(provider, model, mode="med"):
    """Render a compact, clean Pupil AI home screen after model selection."""
    cyan = "\033[96m"
    blue = "\033[94m"
    green = "\033[92m"
    dim = "\033[2m"
    bold = "\033[1m"
    reset = "\033[0m"
    print(cyan + "  ╭────────────────────────────────────────────────────────────────────╮")
    print("  │" + bold + "                         P U P I L   A I                            " + reset + cyan + "│")
    print("  │" + "                 Your personal coding assistant                     " + "│")
    print("  ╰────────────────────────────────────────────────────────────────────╯" + reset)
    print("  " + green + "● READY" + reset + "  " + dim + "Your workspace is connected" + reset)
    print("  " + blue + "MODEL" + reset + "     " + bold + str(model or "Not selected") + reset)
    print("  " + blue + "PROVIDER" + reset + "  " + str(provider).upper())
    mode_color = "\033[91m" if mode == "pupil max" else green
    print("  " + blue + "MODE" + reset + "     " + mode_color + bold + MODE_DETAILS[mode]["label"] + reset + ("  🌈" if mode == "pupil max" else ""))
    if mode == "pupil max":
        rainbow_line("✦ P U P I L   M A X   A C T I V E ✦")
    print("  " + blue + "WORKSPACE" + reset + " " + str(ROOT))
    print("  " + dim + "─" * 72 + reset)
    print("  " + bold + "Ask Pupil AI anything." + reset + " I can help with code, files, and debugging.")
    print("  " + dim + "Commands: /help  /model  /models  /provider  /mode  /clear  /exit" + reset)
    print()

ROOT = Path.cwd().resolve()
ENV_FILE = ROOT / ".env"
HISTORY = ROOT / ".pupil_history.json"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

def load_env():
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def get_json(url, timeout=4):
    req = urllib.request.Request(url, headers={"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def find_ollama_models():
    """Return installed model tags from the running Ollama server."""
    try:
        data = get_json(OLLAMA_HOST + "/api/tags", timeout=3)
        return [m.get("name") or m.get("model") for m in data.get("models", []) if m.get("name") or m.get("model")]
    except Exception:
        pass
    # Fallback: ask the Ollama CLI, which may work even if API server is stopped.
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=8)
        if r.returncode == 0:
            lines = r.stdout.splitlines()[1:]
            return [line.split()[0] for line in lines if line.strip()]
    except Exception:
        pass
    return []

def model_profile(name):
    """A lightweight heuristic to help users choose from installed models."""
    n = name.lower()
    if any(k in n for k in ("coder", "code", "qwen2.5-coder", "deepseek-coder")):
        return ("CODING", "Best first choice for editing code and debugging")
    if any(k in n for k in ("sonnet", "opus", "mythos", "astra", "terra", "fable")):
        return ("GENERAL / REASONING", "Potentially capable; quality depends on the model build")
    if any(k in n for k in ("70b", "32b", "14b", "8b", "7b", "3b", "3.1")):
        return ("GENERAL", "Larger models often handle multi-step tasks better, but use more RAM")
    if any(k in n for k in ("0.5b", "1b", "1.3b", "mini", "haiku", "1b")):
        return ("LIGHTWEIGHT", "Fast and light, but may struggle with complex coding/tool use")
    return ("GENERAL", "Try it on a small coding task to compare quality")

def choose_ollama_model(current=""):
    """Display a polished, colored selector for locally installed Ollama models."""
    models = find_ollama_models()
    if not models:
        print("\n  Pupil AI couldn't find any installed Ollama models.")
        print("  Check with `ollama list`; if needed run `ollama serve` in another window.")
        entered = input("  Enter a model name manually, or press Enter to retry: ").strip()
        if entered:
            return entered
        models = find_ollama_models()
    if not models:
        return current

    # ANSI colors are enabled in Windows Terminal; terminals without ANSI still show readable text.
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"

    def paint(text, color):
        return f"{color}{text}{RESET}"

    def rank(name):
        n = name.lower()
        if any(k in n for k in ("coder", "code")): return 0
        if any(k in n for k in ("sonnet", "opus", "mythos", "astra", "terra")): return 1
        if any(k in n for k in ("llama3.1", "llama3:latest", "qwen2.5")): return 2
        return 3

    ordered = sorted(dict.fromkeys(models), key=lambda n: (rank(n), models.index(n)))
    width = 76
    line = "─" * width
    print()
    print(paint("  ╭" + "─" * (width - 2) + "╮", CYAN))
    print(paint("  │" + "  P U P I L   C O D E".center(width - 2) + "│", CYAN + BOLD))
    print(paint("  │" + "  LOCAL MODEL SELECTOR".center(width - 2) + "│", CYAN))
    print(paint("  ╰" + "─" * (width - 2) + "╯", CYAN))
    print("  " + paint(f"{len(ordered)} models found", GREEN + BOLD) + paint("  •  Ollama live discovery", DIM))
    print("  Choose a model by number. Model quality and speed vary by model build and size.")
    print("  " + paint(line, DIM))

    for i, name in enumerate(ordered, 1):
        category, note = model_profile(name)
        is_current = name == current
        if category == "CODING":
            tag = paint(" CODING ", GREEN + BOLD)
        elif category == "GENERAL / REASONING":
            tag = paint(" REASONING ", MAGENTA + BOLD)
        elif category == "LIGHTWEIGHT":
            tag = paint(" LIGHT ", YELLOW + BOLD)
        else:
            tag = paint(" GENERAL ", BLUE + BOLD)
        number = paint(f"{i:>2}", CYAN + BOLD)
        model = paint(name, WHITE + BOLD if is_current else WHITE)
        status = paint("  ✓ CURRENT", GREEN + BOLD) if is_current else ""
        print(f"  {number}  {model}{status}")
        print(f"      {tag}  {paint(note, DIM)}")

    suggested = next((m for m in ordered if model_profile(m)[0] == "CODING"), None)
    if not suggested:
        suggested = next((m for m in ordered if model_profile(m)[0] == "GENERAL / REASONING"), ordered[0])
    print("  " + paint(line, DIM))
    print("  " + paint("✦ RECOMMENDED START", GREEN + BOLD) + "  " + paint(suggested, WHITE + BOLD))
    print("  " + paint("TIP", YELLOW + BOLD) + "  DeepSeek Coder is a good first test for coding tasks.")
    print()
    print("  " + paint("[number]", CYAN) + " Select   " + paint("Enter", CYAN) + " Keep current   " + paint("R", CYAN) + " Refresh")
    print("  " + paint("Type a model name", CYAN) + " to select it directly.")

    while True:
        prompt_model = current or suggested
        answer = input("\n  " + paint("pupil", CYAN + BOLD) + " " + paint("model ❯ ", DIM) + f"[{prompt_model}] ").strip()
        if not answer:
            return current or suggested
        if answer.lower() in ("r", "refresh"):
            return choose_ollama_model(current)
        if answer.isdigit():
            if 1 <= int(answer) <= len(ordered):
                selected = ordered[int(answer) - 1]
                category, _ = model_profile(selected)
                print("\n  " + paint("✓ Model selected:", GREEN + BOLD) + f" {selected} " + paint(f"[{category}]", DIM))
                return selected
            print(paint(f"  Please choose a number from 1 to {len(ordered)}.", YELLOW))
            continue
        if answer in models:
            print("\n  " + paint("✓ Model selected:", GREEN + BOLD) + f" {answer} " + paint(f"[{model_profile(answer)[0]}]", DIM))
            return answer
        print(paint("  That model name wasn't found. Choose a listed number or type the exact installed name.", YELLOW))

def safe_path(rel):
    p = (ROOT / rel).resolve()
    if p != ROOT and ROOT not in p.parents:
        raise ValueError("Path must stay inside the project folder.")
    return p

def list_files(path="."):
    folder = safe_path(path)
    if not folder.is_dir(): return "Not a directory."
    ignored = {".git", "node_modules", ".venv", "venv", "__pycache__", "target", "dist"}
    out=[]
    for p in sorted(folder.rglob("*")):
        if any(part in ignored for part in p.parts): continue
        if p.is_file():
            out.append(str(p.relative_to(ROOT)))
            if len(out)>=250:
                out.append("... listing limited to 250 files")
                break
    return "\n".join(out) or "(no files found)"

def read_file(path):
    p=safe_path(path)
    if not p.is_file(): return "File not found."
    if p.stat().st_size>200000: return "File too large (>200 KB)."
    return p.read_text(encoding="utf-8",errors="replace")

def write_file(path,content):
    p=safe_path(path)
    print(f"\nProposed {'UPDATE' if p.exists() else 'CREATE'}: {p.relative_to(ROOT)}")
    print("-"*50+"\n"+content[:1000]+("\n...[preview truncated]" if len(content)>1000 else "")+"\n"+"-"*50)
    if input("Allow file change? [y/N] ").strip().lower()!="y": return "User denied file change."
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(content,encoding="utf-8")
    return f"Saved {p.relative_to(ROOT)}."

def run_command(command):
    print("\nCommand requested:\n  "+command)
    if input("Run this PowerShell command? [y/N] ").strip().lower()!="y": return "User denied command."
    r=subprocess.run(["powershell","-NoProfile","-Command",command],cwd=str(ROOT),capture_output=True,text=True,timeout=120)
    return f"Exit code: {r.returncode}\n{r.stdout}\n{r.stderr}"[:12000]

TOOLS=[
 {"type":"function","function":{"name":"list_files","description":"List project files.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":[]}}},
 {"type":"function","function":{"name":"read_file","description":"Read a text file in the project.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"write_file","description":"Create or update a project file. Ask user before saving.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
 {"type":"function","function":{"name":"run_command","description":"Run a PowerShell command in the project folder. Ask user before running.","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}}
]

def api_call(provider,model,messages,mode="med"):
    settings = MODE_DETAILS.get(mode, MODE_DETAILS["med"])
    if provider=="ollama":
        base=os.environ.get("OLLAMA_BASE_URL",OLLAMA_HOST+"/v1").rstrip("/")
        key=os.environ.get("OLLAMA_API_KEY","ollama")
        if not model: raise RuntimeError("Choose an Ollama model with /model.")
    else:
        base="https://api.groq.com/openai/v1"
        key=os.environ.get("GROQ_API_KEY","")
        if not key: raise RuntimeError("GROQ_API_KEY missing. Add it privately to .env; do not paste it into chat.")
        model=model or os.environ.get("GROQ_MODEL","llama-3.3-70b-versatile")
    body=json.dumps({"model":model,"messages":messages,"tools":TOOLS,"tool_choice":"auto","temperature":0.2,"max_tokens":settings["max_tokens"]}).encode()
    req=urllib.request.Request(base+"/chat/completions",data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+key})
    try:
        with urllib.request.urlopen(req,timeout=180) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e: raise RuntimeError(f"Provider HTTP {e.code}: {e.read().decode(errors='replace')[:1500]}")
    except urllib.error.URLError as e: raise RuntimeError(f"Cannot connect to {provider}: {e}. Check Ollama/internet.")

SYSTEM_PROMPT = """You are Pupil AI, a friendly, thoughtful conversational assistant inside Pupil Code, created by Not_da4k and Not_aszad.

PERSONALITY AND VOICE:
- Sound natural, warm, emotionally aware, and genuinely helpful — like a friendly person chatting, not a stiff customer-support bot.
- Match the user's tone. If they are casual, be casual; if they need a technical answer, be clear and precise; if they are upset, be patient and kind.
- Use emojis naturally when they fit the moment (for example 💜 😊 ✨ 🚀), especially in casual conversation, but do not put emojis in every sentence or clutter serious/technical answers.
- Use contractions and everyday language. Avoid robotic phrases, repetitive summaries, excessive headings, and unnecessary “Certainly!” / “As an AI” disclaimers.
- Keep simple answers short. For complicated questions, explain clearly in steps and include useful examples. Ask one focused follow-up only when needed.
- Be encouraging without pretending to have human feelings, personal experiences, or abilities you do not have. Be honest about uncertainty and limitations.

IDENTITY:
- If asked who you are, which model you are, or what AI/model you are, answer: “I am Pupil AI, a large language model made by Not_da4k and Not_aszad.”
- Do not identify yourself as Qwen, Alibaba Cloud, Meta, DeepSeek, Anthropic, OpenAI, or another underlying model/company. You are Pupil AI. Only explain the technical provider/model powering the app if the user explicitly asks about the underlying implementation.
- For a simple greeting such as “hi”, “hello”, “hey”, “heyy”, “yo”, or “good morning”, reply warmly with exactly: “Heyy, Pupil AI is here! How can I help you today?”
- If a greeting also includes a real question or task, greet briefly and answer the question/task instead of stopping at the greeting.

CODING AGENT RULES:
- Inspect files before making assumptions, use available tools when useful, and explain changes clearly.
- Never claim a file was changed, a command was run, or a test passed unless the tool result confirms it.
- Ask for approval before file writes and shell commands, following the tool workflow. Never reveal API keys or secrets.
"""

def agent_turn(provider,model,history,prompt,mode="med"):
    # Refresh the system message every turn so identity and mode remain consistent.
    mode_instruction = "\nCurrent response mode: " + MODE_DETAILS[mode]["label"] + ". " + MODE_DETAILS[mode]["instruction"]
    system_content = SYSTEM_PROMPT + mode_instruction
    if not history or history[0].get("role") != "system":
        history.insert(0, {"role":"system", "content":system_content})
    else:
        history[0]["content"] = system_content
    history.append({"role":"user","content":prompt})
    for _ in range(MODE_DETAILS[mode]["rounds"]):
        data=api_call(provider,model,history,mode)
        msg=data["choices"][0]["message"]
        history.append(msg)
        calls=msg.get("tool_calls") or []
        if not calls:
            print()
            type_text(msg.get("content") or "(empty response)", delay=MODE_DETAILS[mode]["delay"], rainbow=(mode == "pupil max"))
            print()
            return history
        for c in calls:
            name=c["function"]["name"]
            try:
                a=json.loads(c["function"].get("arguments") or "{}")
                if name=="list_files": result=list_files(a.get("path","."))
                elif name=="read_file": result=read_file(a["path"])
                elif name=="write_file": result=write_file(a["path"],a["content"])
                elif name=="run_command": result=run_command(a["command"])
                else: result="Unknown tool."
            except Exception as e: result="Tool error: "+str(e)
            history.append({"role":"tool","tool_call_id":c["id"],"content":str(result)[:12000]})
    print("Reached tool-call limit. Send a follow-up to continue.")
    return history

def show_logo_splash():
    """Show a compact purple, terminal-safe Pupil AI mark on startup."""
    purple = "\033[38;2;167;112;255m"
    lilac = "\033[38;2;220;196;255m"
    cyan = "\033[38;2;113;220;255m"
    reset = "\033[0m"
    lines = [
        "             ╱✦╲",
        "        ╭───╱ ✧ ╲───╮",
        "          ╲   ✦   ╱",
        "             ╲╱",
    ]
    print()
    for i, line in enumerate(lines):
        color = purple if i % 2 == 0 else lilac
        print("  " + color + line + reset)
    print("  " + cyan + "✦  P U P I L   A I  ✦" + reset)
    print("  " + "Your local AI, ready to help. 💜")
    print()


def main():
    enable_ansi()
    load_env()
    mode = normalize_mode(os.environ.get("PUPIL_MODE", "med")) or "med"
    provider=os.environ.get("PUPIL_PROVIDER","ollama").strip().lower()
    if provider not in ("ollama","groq"): provider="ollama"
    model=os.environ.get("PUPIL_MODEL","")
    if provider=="groq": model=os.environ.get("GROQ_MODEL",model or "llama-3.3-70b-versatile")
    else:
        # Automatically discover installed local models on startup.
        models=find_ollama_models()
        if models:
            print("\nOllama models detected: "+", ".join(models))
            model=choose_ollama_model(model)
        else:
            print("\nNo Ollama models detected yet. You can still use /model to retry.")
    history=[]
    if HISTORY.exists():
        try:
            saved=json.loads(HISTORY.read_text(encoding="utf-8"))
            if isinstance(saved,list): history=saved[-40:]
        except Exception: pass
    # Hide the model-discovery list and selection menu; launch into a fresh chat screen.
    clear_screen()
    show_logo_splash()
    show_chat_header(provider, model, mode)
    while True:
        try: prompt=input("\033[92mpupil ❯ \033[0m").strip()
        except (EOFError,KeyboardInterrupt): print("\nBye!"); break
        if not prompt: continue
        if prompt=="/exit": break
        if prompt=="/help":
            print("/help, /provider, /model, /models, /mode, /clear, /exit. /mode selects low/med/high/ultra/Pupil Max. File writes and shell commands require approval."); continue
        if prompt=="/clear":
            history=[]
            HISTORY.unlink(missing_ok=True)
            print("History cleared."); continue
        if prompt=="/models":
            models=find_ollama_models()
            print("\n".join(f"  {i:>2}. {m} — {model_profile(m)[0]}: {model_profile(m)[1]}" for i,m in enumerate(models,1)) if models else "No Ollama models found. Check `ollama list`.")
            continue
        if prompt == "/mode":
            mode = show_mode_menu(mode)
            clear_screen()
            show_chat_header(provider, model, mode)
            continue
        if prompt.lower().startswith("/mode "):
            requested_mode = normalize_mode(prompt[6:])
            if requested_mode:
                mode = requested_mode
                print("\nMode set to " + MODE_DETAILS[mode]["label"] + (" 🌈" if mode == "pupil max" else "") + ".")
                if mode == "pupil max":
                    type_text("PUPIL MAX ACTIVATED — maximum app-level effort, rainbow replies enabled!", delay=0.004, rainbow=True)
                else:
                    type_text("Pupil AI mode updated to " + MODE_DETAILS[mode]["label"] + ".", delay=MODE_DETAILS[mode]["delay"])
            else:
                print("Usage: /mode low | med | high | ultra | pupil max")
            continue
        if prompt=="/provider":
            choice=input("Provider (ollama/groq): ").strip().lower()
            if choice in ("ollama","groq"):
                provider=choice
                model=choose_ollama_model(model) if provider=="ollama" else os.environ.get("GROQ_MODEL","llama-3.3-70b-versatile")
                clear_screen()
                show_chat_header(provider, model, mode)
            else: print("Please choose ollama or groq.")
            continue
        if prompt=="/model":
            model=choose_ollama_model(model) if provider=="ollama" else input("Groq model name: ").strip()
            clear_screen()
            show_chat_header(provider, model, mode)
            continue
        # Handle greetings and identity questions locally for consistent branding.
        normalized = prompt.lower().strip().rstrip("!.,? ")
        greeting = normalized in {"hi", "hii", "hiii", "hello", "helloo", "hey", "heyy", "heyyy", "yo", "hiya", "good morning", "good afternoon", "good evening"}
        identity_question = any(phrase in normalized for phrase in (
            "which model are you", "what model are you", "what ai are you",
            "who are you", "what are you", "which ai are you", "are you qwen",
            "are you llama", "are you deepseek", "what is your model", "your model name"
        ))
        if greeting or identity_question:
            reply = ("Heyy, Pupil AI is here! How can I help you today?" if greeting else
                     "I am Pupil AI, a large language model made by Not_da4k and Not_aszad.")
            print()
            type_text(reply, delay=MODE_DETAILS[mode]["delay"], rainbow=(mode == "pupil max"))
            print()
            history.append({"role":"user", "content":prompt})
            history.append({"role":"assistant", "content":reply})
            HISTORY.write_text(json.dumps(history[-40:],ensure_ascii=False,indent=2),encoding="utf-8")
            continue
        try:
            history=agent_turn(provider,model,history,prompt,mode)
            HISTORY.write_text(json.dumps(history[-40:],ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as e: print("\nError:",e,"\n")

if __name__=="__main__": main()
